"""
HammingCode — Código de Hamming(7,4)

Código lineal que codifica 4 bits de datos en 7 bits de codeword,
añadiendo 3 bits de paridad. Corrige 1 error y detecta 2 por bloque.

Estructura del codeword (posiciones 1-indexadas):
    p1  p2  d1  p3  d2  d3  d4
    1   2   3   4   5   6   7

Bits de paridad:
    p1 cubre: pos 1, 3, 5, 7   → paridad par sobre d1, d2, d4
    p2 cubre: pos 2, 3, 6, 7   → paridad par sobre d1, d3, d4
    p3 cubre: pos 4, 5, 6, 7   → paridad par sobre d2, d3, d4

El síndrome (s1, s2, s3) indica la posición del error en binario.
Si síndrome = 000 → sin error. Si síndrome = 101 → error en pos 5.
"""
from __future__ import annotations
import numpy as np
from .base import ErrorCorrectingCode, EncodedBlock, DecodedBlock, CodingStats


class HammingCode(ErrorCorrectingCode):
    """
    Implementación desde cero de Hamming(7,4).

    Matriz generadora G (4×7) y matriz de paridad H (3×7)
    """

    # Matrices del código Taller 2

    # Matriz generadora G (4 filas de datos × 7 columnas de codeword)
    # Cada fila de datos d se codifica como c = d @ G (mod 2)
    G = np.array([
        [1, 0, 0, 0, 1, 1, 1],
        [0, 1, 0, 0, 0, 1, 1],
        [0, 0, 1, 0, 1, 0, 1],
        [0, 0, 0, 1, 1, 1, 0]
    ], dtype=int)

    # Matriz de paridad H (3×7): H @ c^T = 0 si c es codeword válido
    # Columnas = representación binaria de posición 1..7
    H = np.array([
        [1, 0, 1, 1, 1, 0, 0],
        [1, 1, 0, 1, 0, 1, 0],
        [1, 1, 1, 0, 0, 0, 1]
    ], dtype=int)

    def __init__(self) -> None:
        # Reconstruir G correctamente a partir de la posición sistemática
        # Posiciones de datos: 3, 5, 6, 7 → índices 0-based: 2, 4, 5, 6
        # Posiciones de paridad: 1, 2, 4 → índices 0-based: 0, 1, 3
        self._data_pos   = [2, 4, 5, 6]   # índices 0-based en el codeword
        self._parity_pos = [0, 1, 3]

    # ── Propiedades ────────────────────────────────────────────────────────

    @property
    def n(self) -> int: return 7    # longitud del codeword
    @property
    def k(self) -> int: return 4    # bits de datos por bloque
    @property
    def t(self) -> int: return 1    # errores corregibles por bloque

    # ── Encode ─────────────────────────────────────────────────────────────

    def encode(self, data_bits: str) -> EncodedBlock:
        """
        Codifica la cadena de bits de datos en bloques de k=4 bits.
        Añade 3 bits de paridad por bloque → codewords de 7 bits.

        Args:
            data_bits: cadena de bits ('1011...')

        Returns:
            EncodedBlock con los codewords concatenados.
        """
        if not data_bits:
            raise ValueError("data_bits está vacío.")

        padded   = self.pad_bits(data_bits, self.k)
        blocks   = self.split_blocks(padded, self.k)
        codewords = []

        for block in blocks:
            d = [int(b) for b in block]
            cw = self._encode_block(d)
            codewords.append(''.join(str(b) for b in cw))

        codeword_bits = ''.join(codewords)
        return EncodedBlock(
            data_bits     = data_bits,
            codeword_bits = codeword_bits,
            block_size    = self.k,
            codeword_size = self.n,
            rate          = self.rate,
        )

    def _encode_block(self, d: list[int]) -> list[int]:
        """
        Codifica un bloque de 4 bits en un codeword de 7 bits.
        Coloca datos en posiciones 3,5,6,7 y calcula paridades en 1,2,4.
        """
        cw = [0] * 7
        # Colocar bits de datos
        for i, pos in enumerate(self._data_pos):
            cw[pos] = d[i]
        # Calcular bits de paridad (paridad par)
        # p1 (pos 0): cubre posiciones 0, 2, 4, 6 (1, 3, 5, 7 en 1-indexed)
        cw[0] = (cw[2] + cw[4] + cw[6]) % 2
        # p2 (pos 1): cubre posiciones 1, 2, 5, 6
        cw[1] = (cw[2] + cw[5] + cw[6]) % 2
        # p3 (pos 3): cubre posiciones 3, 4, 5, 6
        cw[3] = (cw[4] + cw[5] + cw[6]) % 2
        return cw

    # ── Decode ─────────────────────────────────────────────────────────────

    def decode(self, received_bits: str) -> DecodedBlock:
        """
        Decodifica y corrige errores en los bits recibidos.
        Divide en bloques de n=7 bits, calcula síndrome y corrige.

        Args:
            received_bits: bits recibidos del canal (longitud múltiplo de 7)

        Returns:
            DecodedBlock con los datos recuperados y métricas de corrección.
        """
        if not received_bits:
            raise ValueError("received_bits está vacío.")

        # Padding si es necesario (bits extra por compresión Tunstall, etc.)
        padded = self.pad_bits(received_bits, self.n)
        blocks = self.split_blocks(padded, self.n)

        all_corrected = []
        all_data      = []
        all_syndromes = []
        total_detected  = 0
        total_corrected = 0
        uncorrectable   = False

        for block in blocks:
            r = [int(b) for b in block]
            syn, corrected, detected, fixed, bad = self._decode_block(r)
            all_syndromes.append(syn)
            all_corrected.append(''.join(str(b) for b in corrected))
            # Extraer datos (posiciones 2, 4, 5, 6)
            data_bits_block = ''.join(str(corrected[p]) for p in self._data_pos)
            all_data.append(data_bits_block)
            total_detected  += detected
            total_corrected += fixed
            if bad:
                uncorrectable = True

        return DecodedBlock(
            received_bits   = received_bits,
            corrected_bits  = ''.join(all_corrected),
            data_bits       = ''.join(all_data),
            syndrome        = '|'.join(all_syndromes[:5]) + ('|...' if len(all_syndromes)>5 else ''),
            errors_detected = total_detected,
            errors_corrected= total_corrected,
            success         = not uncorrectable,
            uncorrectable   = uncorrectable,
        )

    def _decode_block(self, r: list[int]) -> tuple:
        """
        Decodifica un bloque de 7 bits recibido.

        Returns:
            (syndrome_str, corrected, errors_detected, errors_corrected, uncorrectable)
        """
        r = list(r)  # copia mutable
        # Calcular síndrome: s = H @ r^T (mod 2)
        s1 = (r[0] + r[2] + r[4] + r[6]) % 2
        s2 = (r[1] + r[2] + r[5] + r[6]) % 2
        s3 = (r[3] + r[4] + r[5] + r[6]) % 2
        syndrome_val = s1 * 4 + s2 * 2 + s3   # número de posición del error (1-indexed)
        syndrome_str = f"{s1}{s2}{s3}"

        detected  = 0
        corrected_count = 0
        uncorrectable   = False

        if syndrome_val != 0:
            detected = 1
            if 1 <= syndrome_val <= 7:
                # Corregir bit en la posición indicada (1-indexed → 0-indexed)
                r[syndrome_val - 1] ^= 1
                corrected_count = 1
            else:
                uncorrectable = True

        return syndrome_str, r, detected, corrected_count, uncorrectable

    # ── Syndrome ───────────────────────────────────────────────────────────

    def syndrome(self, codeword_bits: str) -> str:
        """
        Calcula el síndrome de un codeword de 7 bits.
        '000' = sin error, otro valor indica posición del error.
        """
        if len(codeword_bits) != self.n:
            raise ValueError(f"Se esperan {self.n} bits, recibidos {len(codeword_bits)}")
        r = [int(b) for b in codeword_bits]
        s1 = (r[0] + r[2] + r[4] + r[6]) % 2
        s2 = (r[1] + r[2] + r[5] + r[6]) % 2
        s3 = (r[3] + r[4] + r[5] + r[6]) % 2
        return f"{s1}{s2}{s3}"

    # ── Evaluate ───────────────────────────────────────────────────────────

    def evaluate(self, original_bits: str, decoded_bits: str, ber_before: float) -> CodingStats:
        """
        Calcula métricas globales comparando bits originales con decodificados.
        """
        # Alinear longitudes
        min_len = min(len(original_bits), len(decoded_bits))
        errors_after = sum(o != d for o, d in zip(original_bits[:min_len], decoded_bits[:min_len]))
        ber_after = errors_after / min_len if min_len > 0 else 0.0

        total_blocks     = max(1, (len(original_bits) + self.k - 1) // self.k)
        corrected_blocks = 0  # se actualiza externamente si se quiere desglose
        failed_blocks    = 0

        return CodingStats(
            ber_before       = ber_before,
            ber_after        = ber_after,
            coding_gain_db   = self.compute_coding_gain(ber_before, ber_after),
            total_blocks     = total_blocks,
            corrected_blocks = corrected_blocks,
            failed_blocks    = failed_blocks,
        )