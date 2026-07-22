"""
M5 — Dashboard Streamlit

Wizard de una sola página: configura fuente → codificación → canal,
ejecuta el pipeline completo (M1-M4) vía core.simulator.Simulator y
muestra el reporte consolidado (M5) vía metrics.pipeline_metrics.PipelineMetrics.
"""

import sys
import tempfile
from pathlib import Path

# Streamlit executes this script directly (e.g. `streamlit run ui/app.py`), so
# the project root — one level up — is not on sys.path by default like it is
# when running `main.py` from the root. Add it so the top-level packages
# (core, source, s_compression, channel, coding, metrics) resolve regardless
# of the caller's working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from core.simulator import Simulator
from source import TextReader, ImageReader, BitsReader
from s_compression import HuffmanCodec, ShannonFanoCodec, TunstallCodec
from coding import HammingCode
from channel import BSChannel
from metrics.pipeline_metrics import PipelineMetrics


st.set_page_config(
    page_title="Simulador de Transmisión Digital",
    page_icon=":material/network_check:",
    layout="wide",
)


# ── Sección 1: Fuente ────────────────────────────────────────────────────────

def render_source():
    tipo = st.radio("Tipo de fuente", ["Texto", "Imagen", "Bits"], horizontal=True)

    if tipo == "Texto":
        lowercase = st.checkbox("Convertir a minúsculas")
        modo = st.radio(
            "Origen del texto", ["Escribir texto", "Cargar archivo TXT"], horizontal=True
        )
        if modo == "Escribir texto":
            texto = st.text_area("Ingrese el texto")
        else:
            archivo = st.file_uploader("Archivo de texto", type=["txt"])
            texto = archivo.getvalue().decode("utf-8") if archivo else None
        if not texto:
            return None
        return TextReader(lowercase=lowercase), texto

    if tipo == "Bits":
        modo = st.radio(
            "Origen de los bits", ["Escribir bits", "Cargar archivo TXT"], horizontal=True
        )
        if modo == "Escribir bits":
            bits = st.text_input("Ingrese bits (solo 0 y 1)")
        else:
            archivo = st.file_uploader("Archivo de bits", type=["txt"])
            bits = archivo.getvalue().decode("utf-8").strip() if archivo else None
        if not bits:
            return None
        if any(c not in "01" for c in bits):
            st.error("La secuencia de bits solo puede contener '0' y '1'.")
            return None
        return BitsReader(), bits

    # Imagen
    archivo = st.file_uploader("Imagen", type=["png", "jpg", "jpeg"])
    modo_labels = {
        "Escala de grises (L) — 1 byte/píxel": "L",
        "Color RGB — 3 bytes/píxel": "RGB",
        "Binaria (1) — 1 bit/píxel": "1",
    }
    modo_img = modo_labels[st.selectbox("Modo de lectura", list(modo_labels.keys()))]
    max_pixels = st.number_input(
        "Máximo de píxeles a leer (limita el tiempo de simulación)",
        min_value=10,
        max_value=100_000,
        value=2000,
        step=100,
        help="El pipeline (Hamming + canal) procesa bit a bit en Python puro; "
             "limitar los píxeles evita simulaciones lentas en imágenes grandes.",
    )
    if archivo is None:
        return None

    # Evitar reescribir el archivo temporal en cada rerun de Streamlit.
    if st.session_state.get("_img_file_id") != archivo.file_id:
        suffix = Path(archivo.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(archivo.getvalue())
            st.session_state["_img_tmp_path"] = tmp.name
        st.session_state["_img_file_id"] = archivo.file_id

    return ImageReader(mode=modo_img, max_pixels=int(max_pixels)), st.session_state["_img_tmp_path"]


# ── Sección 2: Codificación fuente ──────────────────────────────────────────

def render_codec():
    tipo = st.selectbox("Algoritmo de compresión", ["Huffman", "Shannon-Fano", "Tunstall"])

    if tipo == "Huffman":
        return HuffmanCodec(), "Huffman"
    if tipo == "Shannon-Fano":
        return ShannonFanoCodec(), "Shannon-Fano"

    k = st.number_input("Longitud de código k (bits)", min_value=1, max_value=16, value=3, step=1)
    return TunstallCodec(int(k)), f"Tunstall k={int(k)}"


# ── Sección 3: Canal ─────────────────────────────────────────────────────────

def render_channel():
    p = st.slider("Probabilidad de error p", min_value=0.0, max_value=0.5, value=0.05, step=0.01)
    fijar_semilla = st.checkbox("Fijar semilla (resultados reproducibles)")
    seed = None
    if fijar_semilla:
        seed = int(st.number_input("Semilla", min_value=0, value=42, step=1))
    st.caption("Corrección de errores: Hamming(7,4) — fija, sin parámetros configurables.")
    return BSChannel(p=p, seed=seed)


# ── Resultados ────────────────────────────────────────────────────────────

def _truncate(bits: str, n: int = 96) -> str:
    return bits[:n] + ("…" if len(bits) > n else "")


def render_results(report, metrics: PipelineMetrics) -> None:
    st.divider()

    header_col, badge_col = st.columns([3, 2])
    header_col.header("Resultados")
    with badge_col:
        st.write("")  # alinea verticalmente los badges con el header
        st.badge(report.codec_name, color="primary")
        p = report.channel_params.get("p")
        if p is not None:
            st.badge(f"BSC p = {p}", color="blue")

    s, cr, tr, cs, decoded = (
        report.source_stats,
        report.compression_result,
        report.transmission,
        report.coding_stats,
        report.decoded,
    )
    cb = cr.codebook
    summary = metrics.summary_dict(report)

    tab_fuente, tab_compresion, tab_canal, tab_resumen = st.tabs(
        ["M1 · Fuente", "M2 · Compresión", "M3/M4 · Canal y Corrección", "M5 · Resumen"]
    )

    with tab_fuente:
        c1, c2, c3 = st.columns(3)
        c1.metric("Entropía H(X)", f"{s.entropy:.4f} bits/símbolo", border=True)
        c2.metric("Tamaño del alfabeto", len(s.alphabet), border=True)
        c3.metric("Símbolos totales", len(s.symbols), border=True)

        probs = sorted(s.probabilities.items(), key=lambda kv: -kv[1])

        top_n = 30
        chart_probs = probs[:top_n]
        st.bar_chart(
            {"Símbolo": [repr(sym) for sym, _ in chart_probs], "P(s)": [p for _, p in chart_probs]},
            x="Símbolo",
            y="P(s)",
            x_label="Símbolo",
            y_label="P(s)",
        )
        if len(probs) > top_n:
            st.caption(f"Mostrando los {top_n} símbolos más probables de {len(probs)} en el alfabeto.")

        st.dataframe(
            {"Símbolo": [repr(sym) for sym, _ in probs], "P(s)": [p for _, p in probs]},
            width="stretch",
        )

    with tab_compresion:
        l_bar_unit = "símbolos/frase" if cb.code_length is not None else "bits/símbolo"
        c1, c2, c3 = st.columns(3)
        c1.metric("Longitud media L̄", f"{cb.avg_length:.4f} {l_bar_unit}", border=True)
        c2.metric("Tasa de compresión", f"{cr.compression_ratio:.3f}:1", border=True)
        c3.metric("Eficiencia", f"{summary['Eficiencia compresión']:.2f}%", border=True)

        st.metric(
            "Bits comprimidos",
            cr.compressed_bits,
            delta=cr.compressed_bits - cr.original_bits,
            delta_color="inverse",
            help=f"Bits originales: {cr.original_bits}",
            border=True,
        )
        max_bits = max(cr.original_bits, cr.compressed_bits) or 1
        st.progress(min(1.0, cr.original_bits / max_bits), text=f"Original: {cr.original_bits} bits")
        st.progress(min(1.0, cr.compressed_bits / max_bits), text=f"Comprimido: {cr.compressed_bits} bits")

        with st.expander(f"Diccionario de codificación ({len(cb.table)} entradas)"):
            st.dataframe(
                {"Símbolo/Frase": [repr(k) for k in cb.table], "Código": list(cb.table.values())},
                width="stretch",
            )
        st.code(_truncate(cr.bits, 128), language=None)

    with tab_canal:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Capacidad del canal C", f"{tr.capacity:.4f} bits/uso", border=True)
        c2.metric("BER (antes)", f"{tr.ber:.6f}", border=True)
        c3.metric(
            "BER (después)",
            f"{cs.ber_after:.6f}",
            delta=f"{cs.ber_after - tr.ber:+.6f}",
            delta_color="inverse",
            border=True,
        )
        c4.metric("Ganancia de codificación", f"{cs.coding_gain_db:.2f} dB", border=True)

        if decoded.success:
            st.success("Estado de la decodificación: ÉXITO")
        else:
            st.error("Estado de la decodificación: FALLO")

        with st.expander("Detalle del bloque codificado/decodificado"):
            st.write(f"Enviado (post-compresión): `{_truncate(cr.bits, 64)}`")
            st.write(f"Recibido: `{_truncate(decoded.received_bits, 64)}`")
            st.write(f"Corregido: `{_truncate(decoded.corrected_bits, 64)}`")
            st.write(f"Síndrome: `{decoded.syndrome}`")
            st.write(
                f"Errores detectados: {decoded.errors_detected} · "
                f"Errores corregidos: {decoded.errors_corrected}"
            )

    with tab_resumen:
        st.dataframe(
            {"Métrica": list(summary.keys()), "Valor": [str(v) for v in summary.values()]},
            width="stretch",
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_csv:
            csv_path = tmp_csv.name
        metrics.export_csv(report, csv_path)
        with open(csv_path, "rb") as f:
            csv_bytes = f.read()
        st.download_button(
            "Descargar métricas (CSV)",
            data=csv_bytes,
            file_name="metricas.csv",
            mime="text/csv",
            icon=":material/download:",
        )


# ── Página principal ─────────────────────────────────────────────────────────

def main() -> None:
    st.title("Simulador de Transmisión Digital")
    st.caption("Compresión · Canal Ruidoso · Corrección de Errores · Teoría de la Codificación")

    col_source, col_codec, col_channel = st.columns(3)

    with col_source, st.container(border=True):
        st.subheader("1. Fuente de información")
        source_result = render_source()

    with col_codec, st.container(border=True):
        st.subheader("2. Codificación fuente")
        codec, codec_label = render_codec()

    with col_channel, st.container(border=True):
        st.subheader("3. Canal ruidoso")
        channel = render_channel()

    if source_result is None:
        st.info("Configure una fuente válida para habilitar la simulación.")

    if st.button(
        "Simular",
        icon=":material/play_arrow:",
        type="primary",
        disabled=source_result is None,
    ):
        reader, input_value = source_result
        try:
            sim = Simulator(reader, codec, HammingCode(), channel)
            sim.run(input_value)

            metrics = PipelineMetrics()
            metrics.register_source(sim._source_stats)
            metrics.register_compression(sim._compressor_stats, codec_label)
            metrics.register_transmission(sim._trans_result)
            coding_stats = sim.code.evaluate(
                sim._compressor_stats.bits,
                sim._decoded_block.data_bits,
                sim._trans_result.ber,
            )
            metrics.register_correction(sim._decoded_block, coding_stats)

            st.session_state["report"] = metrics.build_report()
            st.session_state["metrics"] = metrics
        except (ValueError, TypeError, KeyError, FileNotFoundError) as e:
            st.session_state.pop("report", None)
            st.error(f"Error en la simulación: {e}")

    if "report" in st.session_state:
        render_results(st.session_state["report"], st.session_state["metrics"])


main()
