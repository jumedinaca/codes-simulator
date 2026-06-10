"""
main.py — Inspector de Codec
=============================
Herramienta de línea de comandos para analizar en detalle
un codec específico sobre una fuente de texto.

Uso:
    python main.py --codec huffman --text "AABAABAACAABAABAABAACAAB"
    python main.py --codec tunstall --k 3 --text "AABAABAACAABAABAABAACAAB"
    python main.py --codec shannon  --text "AABAABAACAABAABAABAACAAB"
    python main.py --codec tunstall --k 4 --file mi_texto.txt
    python main.py --codec huffman  --text "hola mundo" --lowercase
    python main.py --compare        --text "AABAABAACAABAABAABAACAAB"
"""

from __future__ import annotations

import argparse
import sys
import os
from math import log2
from typing import Any

# ── Path setup ─────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from source.text_reader        import TextReader
from compression.huffman       import HuffmanCodec
from compression.shannon_fano  import ShannonFanoCodec
from compression.tunstall      import TunstallCodec
from compression.base          import Codebook
from source_pipeline           import SourcePipeline, SourceCompressionReport


# ══════════════════════════════════════════════════════════════════════════════
#  DISPLAY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
PURPLE = "\033[95m"

def c(text: str, color: str) -> str:
    """Envuelve texto en código de color ANSI."""
    return f"{color}{text}{RESET}"

def bar(value: float, max_val: float, width: int = 30, color: str = GREEN) -> str:
    """Barra de progreso ASCII proporcional a value/max_val."""
    filled = int(round(value / max_val * width)) if max_val > 0 else 0
    filled = max(0, min(width, filled))
    return c("█" * filled, color) + c("░" * (width - filled), DIM)

def section(title: str) -> None:
    print(f"\n{c('━' * 60, CYAN)}")
    print(f"  {c(title, BOLD + CYAN)}")
    print(c("━" * 60, CYAN))

def row(label: str, value: str, width: int = 32) -> None:
    print(f"  {c(label, DIM):<{width+9}} {value}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 1 — Fuente
# ══════════════════════════════════════════════════════════════════════════════

def show_source(report: SourceCompressionReport) -> None:
    s = report.source_stats
    section("M1 — FUENTE DE INFORMACIÓN")

    row("Tipo de fuente",    c(s.metadata.get("source_type", "N/A"), YELLOW))
    row("Símbolos totales",  c(str(len(s.symbols)), YELLOW))
    row("Tamaño alfabeto",   c(str(len(s.alphabet)), YELLOW))
    row("Entropía H(X)",     c(f"{s.entropy:.6f}", GREEN) + " bits/símbolo")

    # Barra de entropía normalizada (máx = log2(|A|))
    max_h = log2(len(s.alphabet)) if len(s.alphabet) > 1 else 1.0
    print(f"\n  {'H(X) relativa al máximo:'}")
    print(f"  {bar(s.entropy, max_h, 40, GREEN)}  "
          f"{c(f'{s.entropy/max_h*100:.1f}%', BOLD)}")

    # Tabla de probabilidades
    print(f"\n  {c('Símbolo', BOLD):<18} {c('Frec.', BOLD):<10} "
          f"{c('P(s)', BOLD):<12} {c('Distribución', BOLD)}")
    print(f"  {'─' * 58}")
    max_p = max(s.probabilities.values())
    for sym, prob in sorted(s.probabilities.items(), key=lambda x: -x[1]):
        freq = int(round(prob * len(s.symbols)))
        pbar = bar(prob, max_p, 20, BLUE)
        print(f"  {c(repr(sym), YELLOW):<18} {str(freq):<10} {prob:<12.6f} {pbar}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 2 — Codebook
# ══════════════════════════════════════════════════════════════════════════════

def show_codebook(report: SourceCompressionReport) -> None:
    s  = report.source_stats
    cb = report.codebook

    section(f"M2 — CODEBOOK  [{report.codec_name}]")

    max_code_len = max(len(c_) for c_ in cb.table.values())

    print(f"\n  {c('Entrada', BOLD):<20} {c('Código', BOLD):<20} "
          f"{c('|código|', BOLD):<12} {c('P(entrada)', BOLD):<14} {c('Contribución a L̄', BOLD)}")
    print(f"  {'─' * 70}")

    entries = sorted(cb.table.items(), key=lambda x: len(x[1]))
    for phrase, code in entries:
        # probabilidad de la frase (producto de P de sus símbolos)
        p_phrase = 1.0
        for ch in str(phrase):
            p_phrase *= s.probabilities.get(ch, s.probabilities.get(phrase, 0.0))

        contribution = len(code) * p_phrase
        code_bar     = bar(len(code), max_code_len, 16, PURPLE)

        print(f"  {c(repr(phrase), YELLOW):<20} "
              f"{c(code, GREEN):<20} "
              f"{str(len(code)):<12} "
              f"{p_phrase:<14.6f} "
              f"{contribution:.6f}")

    print(f"\n  {c('Longitud media L̄', DIM):<32} "
          f"{c(f'{cb.avg_length:.6f}', BOLD + GREEN)} bits/símbolo")

    if cb.code_length is not None:
        print(f"  {c('Longitud fija k', DIM):<32} "
              f"{c(str(cb.code_length), BOLD + YELLOW)} bits/codeword")
        print(f"  {c('Entradas en diccionario', DIM):<32} "
              f"{c(str(len(cb.table)), BOLD + YELLOW)}  "
              f"{c(f'(2^{cb.code_length} = {2**cb.code_length})', DIM)}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 3 — Encoding paso a paso
# ══════════════════════════════════════════════════════════════════════════════

def show_encoding(report: SourceCompressionReport, max_steps: int = 20) -> None:
    s   = report.source_stats
    cb  = report.codebook
    r   = report.compression_result

    section("M2 — ENCODING PASO A PASO")

    text    = "".join(str(sym) for sym in s.symbols)
    phrases = sorted(cb.table.keys(), key=len, reverse=True)

    COLORS = [GREEN, CYAN, YELLOW, PURPLE, BLUE]
    steps: list[tuple[str, str, int]] = []    # (frase, código, color_idx)

    i = 0
    ci = 0
    while i < len(text) and len(steps) < max_steps:
        for phrase in phrases:
            if text[i: i + len(phrase)] == phrase:
                steps.append((phrase, cb.table[phrase], ci % len(COLORS)))
                i += len(phrase)
                ci += 1
                break

    total_steps = len(s.symbols) if cb.code_length is None else len(r.bits) // (cb.code_length or 1)

    print(f"\n  Mostrando {min(max_steps, len(steps))} de ~{total_steps} pasos:\n")
    print(f"  {'Paso':<7} {'Frase':<14} {'→':<4} {'Código':<16} {'Acum. bits'}")
    print(f"  {'─' * 56}")

    accum = 0
    for idx, (phrase, code, col) in enumerate(steps, 1):
        accum += len(code)
        print(f"  {c(str(idx), DIM):<16}"
              f"{c(repr(phrase), COLORS[col]):<23}"
              f"{'→':<4}"
              f"{c(code, GREEN):<25}"
              f"{c(str(accum), DIM)}")

    if len(steps) == max_steps and i < len(text):
        print(f"  {c('...  (truncado)', DIM)}")

    # Stream de bits coloreado por frase
    print(f"\n  {c('Bitstream (coloreado por frase):', BOLD)}")
    print(f"  ", end="")
    ci = 0
    bit_cursor = 0
    i = 0
    while i < len(text) and bit_cursor < 120:
        for phrase in phrases:
            if text[i: i + len(phrase)] == phrase:
                code = cb.table[phrase]
                print(c(code, COLORS[ci % len(COLORS)]), end="")
                bit_cursor += len(code)
                i += len(phrase)
                ci += 1
                break
    if bit_cursor >= 120:
        print(c("...", DIM), end="")
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 4 — Decoding verificación
# ══════════════════════════════════════════════════════════════════════════════

def show_decoding(report: SourceCompressionReport) -> None:
    s   = report.source_stats
    cb  = report.codebook
    r   = report.compression_result

    section("M2 — DECODIFICACIÓN Y VERIFICACIÓN")

    original = "".join(str(sym) for sym in s.symbols)
    decoded  = "".join(str(sym) for sym in report.decoded_symbols[: len(s.symbols)])

    status = c("✓  LOSSLESS VERIFICADO", BOLD + GREEN) if report.lossless_verified \
             else c("✗  ERROR EN RECONSTRUCCIÓN", BOLD + RED)
    print(f"\n  {status}\n")

    # Comparación carácter a carácter (primeros 60)
    limit  = 60
    orig_p = original[:limit]
    deco_p = decoded[:limit]

    print(f"  {c('Original :', DIM)}  {c(orig_p, YELLOW)}" +
          (c("...", DIM) if len(original) > limit else ""))
    print(f"  {c('Decodif. :', DIM)}  {c(deco_p, GREEN)}" +
          (c("...", DIM) if len(decoded) > limit else ""))

    # Marcar diferencias
    diff_line = ""
    for o, d in zip(orig_p, deco_p):
        diff_line += c("^", RED) if o != d else " "
    if diff_line.strip():
        print(f"  {c('Diffs    :', DIM)}  {diff_line}")

    mismatches = sum(o != d for o, d in zip(original, decoded))
    print(f"\n  {c('Símbolos distintos:', DIM):<32} "
          f"{c(str(mismatches), RED if mismatches else GREEN)}")
    print(f"  {c('Longitud original:', DIM):<32} {len(original)}")
    print(f"  {c('Longitud decodificada:', DIM):<32} {len(report.decoded_symbols)}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECCIÓN 5 — Métricas finales
# ══════════════════════════════════════════════════════════════════════════════

def show_metrics(report: SourceCompressionReport) -> None:
    s  = report.source_stats
    cb = report.codebook
    r  = report.compression_result

    section("M2 — MÉTRICAS DE COMPRESIÓN")

    h        = s.entropy
    l_bar    = cb.avg_length
    eff      = report.efficiency
    ratio    = r.compression_ratio
    orig     = r.original_bits
    comp     = r.compressed_bits
    redundancy = l_bar - h

    print()
    row("Entropía  H(X)",         c(f"{h:.6f}", GREEN)     + " bits/símbolo")
    row("Long. media  L̄",         c(f"{l_bar:.6f}", YELLOW) + " bits/símbolo")
    row("Redundancia  L̄ − H(X)",  c(f"{redundancy:.6f}", RED if redundancy > 0.01 else GREEN)
                                  + " bits/símbolo")
    row("Eficiencia  H/L̄",        c(f"{eff*100:.2f}%", BOLD + GREEN))
    row("Bits originales",        c(str(orig), DIM))
    row("Bits comprimidos",       c(str(comp), CYAN))
    row("Tasa de compresión",     c(f"{ratio:.4f}x", BOLD + CYAN))
    row("Ahorro",                 c(f"{(1-1/ratio)*100:.1f}%", GREEN) if ratio > 1
                                  else c("sin ahorro", DIM))

    if cb.code_length is not None:
        # Métricas adicionales de Tunstall
        from compression.tunstall import TunstallCodec
        t_rate = cb.code_length / l_bar
        print()
        row("k (bits/codeword)",    c(str(cb.code_length), YELLOW))
        row("Tasa Tunstall  k/L̄",  c(f"{t_rate:.6f}", YELLOW) + " bits/símbolo")
        row("Frases en dicc.",      c(str(len(cb.table)), YELLOW) +
                                    c(f"  / {2**cb.code_length} máximo", DIM))

        # Distribución de longitudes de frases
        dist: dict[int, int] = {}
        for phrase in cb.table:
            dist[len(phrase)] = dist.get(len(phrase), 0) + 1
        print(f"\n  {c('Distribución de longitudes de frases:', BOLD)}")
        for length, count in sorted(dist.items()):
            bbar = bar(count, max(dist.values()), 24, PURPLE)
            print(f"  {c(f'|frase|={length}', DIM):<20} {bbar}  {c(str(count), YELLOW)}")

    # Barra de eficiencia
    print(f"\n  {c('Eficiencia del codec:', BOLD)}")
    print(f"  {bar(eff * 100, 100, 40, GREEN)}  {c(f'{eff*100:.2f}%', BOLD)}")

    # Límite de Shannon
    print(f"\n  {c('Límite de Shannon:', DIM)} L̄ ≥ H(X)  →  "
          f"{c(f'{l_bar:.4f}', YELLOW)} ≥ {c(f'{h:.4f}', GREEN)}  "
          f"{'✓' if l_bar >= h - 1e-9 else c('✗ VIOLACIÓN', RED)}")


# ══════════════════════════════════════════════════════════════════════════════
#  COMPARATIVA
# ══════════════════════════════════════════════════════════════════════════════

def show_compare(text: str, reader: TextReader) -> None:
    codecs = [
        ("Huffman",        HuffmanCodec()),
        ("Shannon-Fano",   ShannonFanoCodec()),
        ("Tunstall k=2",   TunstallCodec(k=2)),
        ("Tunstall k=3",   TunstallCodec(k=3)),
        ("Tunstall k=4",   TunstallCodec(k=4)),
    ]

    reports = []
    for name, codec in codecs:
        try:
            p = SourcePipeline(reader=reader, codec=codec)
            r = p.run(text)
            reports.append((name, r))
        except ValueError as e:
            reports.append((name, None))

    section("COMPARATIVA DE CODECS")

    h = reports[0][1].source_stats.entropy if reports[0][1] else 0
    print(f"\n  {c('Entropía fuente H(X):', DIM)} {c(f'{h:.6f}', GREEN)} bits/símbolo\n")

    hdr = (f"  {c('Codec', BOLD):<30} {c('L̄', BOLD):<14} "
           f"{c('Ratio', BOLD):<12} {c('Eficiencia', BOLD):<14} "
           f"{c('Bits out', BOLD):<12} {c('OK', BOLD)}")
    print(hdr)
    print(f"  {'─' * 72}")

    best_eff   = max((r.efficiency for _, r in reports if r), default=0)
    best_ratio = max((r.compression_result.compression_ratio for _, r in reports if r), default=0)

    for name, r in reports:
        if r is None:
            print(f"  {c(name, DIM):<30} {c('k insuficiente para este alfabeto', DIM)}")
            continue
        cb     = r.codebook
        res    = r.compression_result
        eff    = r.efficiency
        ratio  = res.compression_ratio
        lossless = c("✓", GREEN) if r.lossless_verified else c("✗", RED)
        eff_mark  = c("◀ mejor", BOLD + GREEN) if abs(eff - best_eff) < 1e-6 else ""
        rat_mark  = c("◀ mejor", BOLD + CYAN)  if abs(ratio - best_ratio) < 1e-6 else ""

        print(f"  {c(name, YELLOW):<30}"
              f" {cb.avg_length:<14.6f}"
              f" {c(f'{ratio:.4f}x', CYAN):<21}"
              f" {c(f'{eff*100:.2f}%', GREEN):<23}"
              f" {str(res.compressed_bits):<12}"
              f" {lossless}  {eff_mark}{rat_mark}")

    print()


# ══════════════════════════════════════════════════════════════════════════════
#  ARGPARSE + ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Inspector detallado de codecs de compresión (M1 + M2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py --codec huffman  --text "AABAABAACAAB"
  python main.py --codec tunstall --k 3 --text "AABAABAACAAB"
  python main.py --codec shannon  --text "AABAABAACAAB"
  python main.py --codec tunstall --k 4 --file corpus.txt
  python main.py --compare        --text "AABAABAACAAB"
        """,
    )

    # Fuente
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", "-t",  type=str, help="Texto de entrada directo.")
    src.add_argument("--file", "-f",  type=str, help="Ruta a un archivo .txt de entrada.")

    # Codec
    parser.add_argument(
        "--codec", "-c",
        choices=["huffman", "shannon", "tunstall"],
        help="Codec a inspeccionar.",
    )
    parser.add_argument(
        "--k", type=int, default=3,
        help="Bits por codeword para Tunstall (default: 3).",
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Mostrar tabla comparativa de todos los codecs.",
    )

    # Opciones de visualización
    parser.add_argument(
        "--lowercase", action="store_true",
        help="Convertir texto a minúsculas antes de procesar.",
    )
    parser.add_argument(
        "--steps", type=int, default=20,
        help="Número máximo de pasos del encoding a mostrar (default: 20).",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Desactivar colores ANSI (para redirigir a archivo).",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # Desactivar colores si se pidió
    if args.no_color:
        global RESET, BOLD, DIM, GREEN, CYAN, YELLOW, RED, BLUE, PURPLE
        RESET = BOLD = DIM = GREEN = CYAN = YELLOW = RED = BLUE = PURPLE = ""

    # Leer fuente
    if args.text:
        text = args.text
    else:
        if not os.path.exists(args.file):
            print(c(f"Error: no se encontró el archivo '{args.file}'.", RED))
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read().strip()

    if not text:
        print(c("Error: la fuente está vacía.", RED))
        sys.exit(1)

    reader = TextReader(lowercase=args.lowercase)

    # ── Modo comparativa ──────────────────────────────────────────────────
    if args.compare:
        show_compare(text, reader)
        sys.exit(0)

    # ── Modo inspector individual ─────────────────────────────────────────
    if not args.codec:
        parser.error("Debes indicar --codec o usar --compare.")

    codec_map = {
        "huffman" : HuffmanCodec(),
        "shannon" : ShannonFanoCodec(),
        "tunstall": TunstallCodec(k=args.k),
    }
    codec = codec_map[args.codec]

    print(c(f"\n  Simulador de Transmisión Digital — Inspector M1+M2", BOLD))
    print(c(f"  Codec: {codec.__class__.__name__}", CYAN) +
          (c(f"  k={args.k}", YELLOW) if args.codec == "tunstall" else ""))
    print(c(f"  Fuente: {repr(text[:60])}{'...' if len(text)>60 else ''}", DIM))

    pipeline = SourcePipeline(reader=reader, codec=codec)

    try:
        report = pipeline.run(text)
    except ValueError as e:
        print(c(f"\n  Error al construir el codec: {e}", RED))
        sys.exit(1)

    show_source(report)
    show_codebook(report)
    show_encoding(report, max_steps=args.steps)
    show_decoding(report)
    show_metrics(report)

    print(c("\n" + "━" * 60, CYAN))
    print(c("  Análisis completado.\n", DIM))


if __name__ == "__main__":
    main()