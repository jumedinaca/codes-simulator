"""
SourcePipeline — Pipeline básico M1 → M2
=========================================
Conecta el módulo de fuente (M1) con el módulo de compresión (M2)
y produce un reporte unificado con todas las métricas.

No depende de M3/M4/M5: funciona de forma autónoma para desarrollar
y validar la compresión antes de integrar el canal y la corrección.

Uso rápido:
    from source_pipeline import SourcePipeline
    from source.text_reader      import TextReader
    from compression.huffman     import HuffmanCodec
    from compression.tunstall    import TunstallCodec
    from compression.shannon_fano import ShannonFanoCodec

    # Huffman
    pipeline = SourcePipeline(reader=TextReader(), codec=HuffmanCodec())
    report   = pipeline.run("AABAABAACAABAABAABAACAAB")
    pipeline.print_report(report)

    # Tunstall k=3
    pipeline = SourcePipeline(reader=TextReader(), codec=TunstallCodec(k=3))
    report   = pipeline.run("AABAABAACAABAABAABAACAAB")
    pipeline.print_report(report)

    # Comparativa entre los tres codecs
    SourcePipeline.compare("AABAABAACAABAABAABAACAAB", TextReader())
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from source.base      import SourceReader, SourceStats
from compression.base import SourceCodec, Codebook, CompressionResult


# ── Tipo de reporte ────────────────────────────────────────────────────────

@dataclass
class SourceCompressionReport:
    """
    Reporte unificado de M1 + M2.

    Attributes:
        source_stats      : análisis de la fuente (M1)
        codebook          : diccionario construido por el codec (M2)
        compression_result: resultado de la codificación (M2)
        codec_name        : nombre del algoritmo usado
        efficiency        : H(X) / L̄  (Huffman/SF) o  (k/L̄)/H(X)  (Tunstall)
        decoded_symbols   : símbolos reconstruidos tras decodificar (verificación)
        lossless_verified : True si decoded_symbols == symbols originales
    """
    source_stats:       SourceStats
    codebook:           Codebook
    compression_result: CompressionResult
    codec_name:         str
    efficiency:         float
    decoded_symbols:    list[Any]
    lossless_verified:  bool


# ── Pipeline ───────────────────────────────────────────────────────────────

class SourcePipeline:
    """
    Pipeline M1 → M2: análisis de fuente + compresión sin pérdida.

    Args:
        reader: implementación de SourceReader (M1).
        codec : implementación de SourceCodec  (M2).
    """

    def __init__(self, reader: SourceReader, codec: SourceCodec) -> None:
        self._reader = reader
        self._codec  = codec

    # ── Ejecución ──────────────────────────────────────────────────────────

    def run(self, source: Any) -> SourceCompressionReport:
        """
        Ejecuta el pipeline completo M1 → M2 sobre la fuente dada.

        Pasos:
            1. M1: leer fuente → SourceStats (probabilidades + entropía)
            2. M2: construir codebook con las probabilidades de M1
            3. M2: codificar los símbolos de M1 → CompressionResult
            4. M2: decodificar y verificar que la reconstrucción sea exacta
            5. Calcular eficiencia cruzando H(X) de M1 con L̄ de M2

        Args:
            source: entrada para M1 (str, ruta de imagen, bits, etc.)

        Returns:
            SourceCompressionReport con todos los resultados.
        """
        # ── M1: Análisis de fuente ─────────────────────────────────────────
        stats   = self._reader.read(source)
        symbols = self._reader.to_symbols(source)

        # ── M2: Construir codebook ─────────────────────────────────────────
        codebook = self._codec.build_codebook(stats.probabilities)

        # ── M2: Codificar ──────────────────────────────────────────────────
        result = self._codec.encode(symbols, codebook)

        # ── Eficiencia cruzada M1 × M2 ────────────────────────────────────
        efficiency = self._codec.compute_efficiency(codebook.avg_length, stats.entropy)
        result.efficiency = efficiency

        # ── M2: Decodificar y verificar lossless ──────────────────────────
        decoded  = self._codec.decode(result.bits, codebook)
        # Comparar solo los primeros len(symbols) en caso de padding en Tunstall
        verified = decoded[: len(symbols)] == symbols

        return SourceCompressionReport(
            source_stats       = stats,
            codebook           = codebook,
            compression_result = result,
            codec_name         = self._codec.__class__.__name__,
            efficiency         = efficiency,
            decoded_symbols    = decoded,
            lossless_verified  = verified,
        )

    # ── Reporte en consola ─────────────────────────────────────────────────

    @staticmethod
    def print_report(report: SourceCompressionReport) -> None:
        """
        Imprime un reporte legible en consola con todas las métricas.

        Args:
            report: generado por run().
        """
        SEP  = "─" * 56
        SEP2 = "═" * 56
        s    = report.source_stats
        r    = report.compression_result
        cb   = report.codebook

        print(f"\n{SEP2}")
        print(f"  REPORTE: {report.codec_name}")
        print(SEP2)

        # M1
        print(f"\n  [M1] Fuente")
        print(f"  {'Tipo':<28} {s.metadata.get('source_type', 'N/A')}")
        print(f"  {'Símbolos totales':<28} {len(s.symbols)}")
        print(f"  {'Tamaño del alfabeto':<28} {len(s.alphabet)}")
        print(f"  {'Entropía H(X)':<28} {s.entropy:.6f} bits/símbolo")

        # Probabilidades
        print(f"\n  {'Símbolo':<12} {'P(s)':<12} {'Código':<16} {'|código|'}")
        print(f"  {SEP}")
        for sym, prob in sorted(s.probabilities.items(), key=lambda x: -x[1]):
            code = cb.table.get(sym, cb.table.get(str(sym), '—'))
            print(f"  {str(sym):<12} {prob:<12.6f} {code:<16} {len(code)}")

        # M2
        print(f"\n  [M2] Compresión — {report.codec_name}")
        print(f"  {'Longitud media L̄':<28} {cb.avg_length:.6f} bits/símbolo")
        if cb.code_length is not None:
            print(f"  {'Longitud fija k':<28} {cb.code_length} bits/codeword")
        print(f"  {'Bits originales':<28} {r.original_bits}")
        print(f"  {'Bits comprimidos':<28} {r.compressed_bits}")
        print(f"  {'Tasa de compresión':<28} {r.compression_ratio:.4f}x")
        print(f"  {'Eficiencia':<28} {report.efficiency * 100:.2f} %")
        print(f"  {'Verificación lossless':<28} {'✓ OK' if report.lossless_verified else '✗ FALLA'}")

        # Primeros bits
        preview = r.bits[:64] + ("..." if len(r.bits) > 64 else "")
        print(f"\n  Bits codificados (preview):")
        print(f"  {preview}")
        print(f"{SEP2}\n")

    # ── Comparativa entre codecs ───────────────────────────────────────────

    @staticmethod
    def compare(
        source: Any,
        reader: SourceReader,
        codecs: list[SourceCodec] | None = None,
    ) -> list[SourceCompressionReport]:
        """
        Ejecuta el pipeline con múltiples codecs y muestra una tabla comparativa.

        Args:
            source: fuente a comprimir.
            reader: lector de fuente (M1) compartido.
            codecs: lista de codecs a comparar. Si es None, usa los tres
                    predefinidos: Huffman, ShannonFano, Tunstall(k=3).

        Returns:
            Lista de SourceCompressionReport, uno por codec.
        """
        if codecs is None:
            from compression.huffman      import HuffmanCodec
            from compression.shannon_fano import ShannonFanoCodec
            from compression.tunstall     import TunstallCodec
            codecs = [HuffmanCodec(), ShannonFanoCodec(), TunstallCodec(k=3)]

        reports: list[SourceCompressionReport] = []
        for codec in codecs:
            pipeline = SourcePipeline(reader=reader, codec=codec)
            report   = pipeline.run(source)
            reports.append(report)

        # Tabla comparativa
        SEP2 = "═" * 72
        print(f"\n{SEP2}")
        print(f"  COMPARATIVA DE CODECS")
        print(SEP2)
        header = f"  {'Codec':<22} {'H(X)':<10} {'L̄':<10} {'Ratio':<10} {'Eficiencia':<12} {'Lossless'}"
        print(header)
        print(f"  {'─'*68}")
        for rep in reports:
            cb   = rep.codebook
            r    = rep.compression_result
            mark = "✓" if rep.lossless_verified else "✗"
            print(
                f"  {rep.codec_name:<22}"
                f" {rep.source_stats.entropy:<10.4f}"
                f" {cb.avg_length:<10.4f}"
                f" {r.compression_ratio:<10.4f}"
                f" {rep.efficiency * 100:<12.2f}"
                f" {mark}"
            )
        print(SEP2 + "\n")

        return reports


# ── Punto de entrada rápido ────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from source.text_reader       import TextReader
    from compression.huffman      import HuffmanCodec
    from compression.shannon_fano import ShannonFanoCodec
    from compression.tunstall     import TunstallCodec

    text = sys.argv[1] if len(sys.argv) > 1 else "AABAABAACAABAABAABAACAAB"
    reader = TextReader()

    print(f"Fuente: '{text}'")

    SourcePipeline.compare(
        source = text,
        reader = reader,
        codecs = [
            HuffmanCodec(),
            ShannonFanoCodec(),
            #TunstallCodec(),
        ],
    )
