from math import log2

from InquirerPy import inquirer

from core.simulator import Simulator
from source import *
from s_compression import *
from coding import *
from channel import *


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


def show_source_stats(s: SourceStats) -> None:
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

def show_codebook(codebook: Codebook ) -> None:
    section("DICCIONARIO DE CODIFICACIÓN")

    print(f"{c('Entradas:', BOLD):20} {len(codebook.table)}")
    print(f"{c('Longitud media:', BOLD):20} {codebook.avg_length:.4f} bits/símbolo")

    if codebook.code_length is None:
        print(f"{c('Longitud:', BOLD):20} Variable")
    else:
        print(f"{c('Longitud fija:', BOLD):20} {codebook.code_length} bits")

    print()

    print(
        c(f"{'Símbolo / Frase':<35}", BOLD + BLUE)
        + c(f"{'Código':>20}", BOLD + BLUE)
    )

    print(c("─" * 55, CYAN))

    for symbol, code in sorted(codebook.table.items()):

        symbol = repr(symbol)

        if len(symbol) > 34:
            symbol = symbol[:31] + "..."

        print(
            f"{c(symbol, YELLOW):<44}"
            f"{c(code, GREEN):>12}"
        )

    print(c("─" * 55, CYAN))

def show_compression_result(result: CompressionResult) -> None:
    """Imprime un resumen del resultado de la compresión."""

    section("RESULTADO DE LA COMPRESIÓN")

    ahorro = (
        100 * (1 - result.compressed_bits / result.original_bits)
        if result.original_bits > 0
        else 0
    )

    print(f"{c('Bits originales', BOLD):22}: {result.original_bits}")
    print(f"{c('Bits comprimidos', BOLD):22}: {result.compressed_bits}")
    print(f"{c('Relación compresión', BOLD):22}: {result.compression_ratio:.3f}:1")
    print(f"{c('Ahorro', BOLD):22}: {ahorro:.2f}%")

    if result.efficiency is not None:
        print(f"{c('Eficiencia', BOLD):22}: {result.efficiency:.2%}")

    print(f"{c('Entradas diccionario', BOLD):22}: {len(result.codebook.table)}")

    print()

    print(c("Tamaño del mensaje", BOLD))

    mayor = max(result.original_bits, result.compressed_bits)

    print(
        f"{c('Original  ', BLUE)} "
        f"{bar(result.original_bits, mayor, color=BLUE)} "
        f"{result.original_bits} bits"
    )

    print(
        f"{c('Comprimido', GREEN)} "
        f"{bar(result.compressed_bits, mayor)} "
        f"{result.compressed_bits} bits"
    )

    print()

    print(c("Primeros bits codificados", BOLD))

    vista = result.bits[:128]

    if len(result.bits) > 128:
        vista += "..."

    print(c(vista, YELLOW))

def show_encoded_block(block: EncodedBlock) -> None:
    """Imprime un bloque codificado."""

    section("BLOQUE CODIFICADO")

    redundancia = block.codeword_size - block.block_size

    print(f"{c('Datos originales', BOLD):22}: {block.data_bits}")
    print(f"{c('Palabra código', BOLD):22}: {block.codeword_bits}")

    print()

    print(f"{c('Bloque (k)', BOLD):22}: {block.block_size} bits")
    print(f"{c('Código (n)', BOLD):22}: {block.codeword_size} bits")
    print(f"{c('Redundancia', BOLD):22}: {redundancia} bits")
    print(f"{c('Tasa (k/n)', BOLD):22}: {block.rate:.3f}")

    print()

    print(c("Estructura", BOLD))
    print(
        c(block.data_bits, GREEN)
        + c(" | ", DIM)
        + c(block.codeword_bits[len(block.data_bits):], YELLOW)
    )

def show_decoded_block(block: DecodedBlock) -> None:
    """Imprime el resultado de la decodificación."""

    section("RESULTADO DE LA DECODIFICACIÓN")

    estado = c("✔ ÉXITO", GREEN) if block.success else c("✘ FALLO", RED)

    print(f"{c('Estado', BOLD):22}: {estado}")

    if block.uncorrectable:
        print(f"{c('Corregible', BOLD):22}: {c('NO', RED)}")

    print()

    print(f"{c('Recibido', BOLD):22}: {block.received_bits}")
    print(f"{c('Corregido', BOLD):22}: {block.corrected_bits}")
    print(f"{c('Datos extraídos', BOLD):22}: {block.data_bits}")

    print()

    print(f"{c('Síndrome', BOLD):22}: {block.syndrome}")
    print(f"{c('Errores detectados', BOLD):22}: {block.errors_detected}")
    print(f"{c('Errores corregidos', BOLD):22}: {block.errors_corrected}")

def run_cli():
    section("SIMULADOR DE CODIGOS")
    
    
    #Ask for type of source and its input
    sourceReader, _input = ask_source()

    #Ask for compression algorithm or none
    codec = ask_codec()

    #Ask for coding
    #TODO
    code = HammingCode()

    #Ask for channel
    #TODO
    channel = BSChannel(p=0.2)

    #simulate
    sim = Simulator(sourceReader,codec,code,channel)
    sim.run(_input)

    #Show stats
    show_source_stats(sim._source_stats)
    show_codebook(sim._codebook)
    show_compression_result(sim._compressor_stats)
    show_encoded_block(sim._encoded_block)
    show_decoded_block(sim._decoded_block)
    

def ask_source() -> (SourceReader, str):

    reader = stats = None

    _type = inquirer.select(
    message="Seleccione la fuente:",
    choices=[
        "Texto",
        "Imagen",
        "Bits",
    ],
    ).execute()

    match _type:
        case "Texto":
            reader = TextReader()
            
            modo = inquirer.select(
                message="Fuente de texto:",
                choices=[
                    "Escribir texto",
                    "Cargar archivo TXT",
                ],
            ).execute()

            if modo == "Escribir texto":
                _input = inquirer.text(
                    message="Ingrese el texto:",
                ).execute()

            else:
                _input = inquirer.filepath(
                    message="Seleccione el archivo:",
                    only_files=True,
                ).execute()

        case "Bits":
            reader = BitsReader()
            
            modo = inquirer.select(
                message="Fuente de bits:",
                choices=[
                    "Escribir bits",
                    "Cargar archivo TXT",
                ],
            ).execute()

            if modo == "Escribir bits":
                _input = inquirer.text(
                    message="Ingrese bits:",
                    validate=lambda x: all(c in "01" for c in x),
                    invalid_message="Solo 0 y 1"
                ).execute()

            else:
                while True:
                    path = inquirer.filepath(
                        message="Seleccione el archivo:",
                        only_files=True,
                    ).execute()

                    with open(path, 'r') as f:
                        _input = f.read()

                    if all(c in "01" for c in _input): break    

                    print("Formato no válido.")


        case "Imagen":

            from pathlib import Path
            while True:
                _input = inquirer.filepath(
                    message="Seleccione una imagen:",
                    only_files=True,
                ).execute()

                if Path(_input).suffix.lower() in [".png", ".jpg", ".jpeg"]:
                    break

                print("Formato no válido.")


            modo = inquirer.select(
                message="Modo de lectura:",
                choices=[
                    {
                        "name": "Escala de grises (L) — 1 byte/píxel",
                        "value": "L",
                    },
                    {
                        "name": "Color RGB — 3 bytes/píxel",
                        "value": "RGB",
                    },
                    {
                        "name": "Binaria (1) — 1 bit/píxel",
                        "value": "1",
                    },
                ],
            ).execute()
            reader = ImageReader(mode=modo)

    return reader, _input

def ask_codec() -> SourceCodec:

    _type = inquirer.select(
    message="Seleccione algoritmo de compresion:",
    choices=[
        "Huffman",
        "Shannon-Fano",
        "Tunstall",
    ],
    ).execute()

    match _type:
        case "Huffman":
            return HuffmanCodec()

        case "Shannon-Fano":
            return ShannonFanoCodec()

        case "Tunstall":
            k = inquirer.number(
                message="Longitud (k):",
                min_allowed= 1,
                invalid_message="Solo se permiten enteros > 1",
            ).execute()

            return TunstallCodec(int(k))
