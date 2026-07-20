"""
ShannonFanoCodec
Implementación de la codificación Shannon-Fano.

Ordena los símbolos por probabilidad descendente y divide recursivamente
el conjunto en dos grupos de probabilidad acumulada lo más similar posible,
asignando '0' al grupo superior y '1' al inferior.

Uso:
    codec    = ShannonFanoCodec()
    codebook = codec.build_codebook({'A': 0.4, 'B': 0.3, 'C': 0.2, 'D': 0.1})
    result   = codec.encode(['A', 'B', 'A', 'D'], codebook)
    symbols  = codec.decode(result.bits, codebook)
"""

from __future__ import annotations
from typing import Any

from .base import SourceCodec, Codebook, CompressionResult


class ShannonFanoCodec(SourceCodec):
    """
    Codificador/Decodificador Shannon-Fano.

    Produce códigos libres de prefijo. No garantiza optimalidad global
    (Huffman es siempre igual o mejor), pero es más sencillo de analizar
    ya que la estructura de partición es transparente.
    """

    # ── build_codebook ─────────────────────────────────────────────────────

    def build_codebook(self, probabilities: dict[Any, float]) -> Codebook:
        """
        Construye los códigos Shannon-Fano por partición recursiva.

        Algoritmo:
            1. Ordenar símbolos por probabilidad descendente.
            2. Dividir en dos grupos cuya suma de probabilidades sea
               lo más parecida posible.
            3. Asignar '0' al grupo de mayor prob, '1' al otro.
            4. Repetir recursivamente en cada grupo.

        Args:
            probabilities: mapping símbolo → P(símbolo).

        Returns:
            Codebook con tabla directa, inversa y L̄.

        Raises:
            ValueError: si hay menos de 2 símbolos.
        """
        self.validate_probabilities(probabilities)
        if len(probabilities) < 2:
            raise ValueError("Shannon-Fano requiere al menos 2 símbolos distintos.")

        # Ordenar por probabilidad descendente
        sorted_syms: list[tuple[Any, float]] = sorted(
            probabilities.items(), key=lambda x: x[1], reverse=True
        )

        table: dict[Any, str] = {sym: "" for sym, _ in sorted_syms}
        self._split(sorted_syms, table)

        # Calcular L̄
        avg_length = sum(
            probabilities[sym] * len(code)
            for sym, code in table.items()
        )

        inverse = {code: sym for sym, code in table.items()}

        return Codebook(
            table       = table,
            inverse     = inverse,
            avg_length  = avg_length,
            code_length = None,
        )

    # ── encode ─────────────────────────────────────────────────────────────

    def encode(self, symbols: list[Any], codebook: Codebook) -> CompressionResult:
        """
        Codifica la secuencia de símbolos concatenando sus códigos.

        Args:
            symbols : lista de símbolos de la fuente.
            codebook: construido con build_codebook().

        Returns:
            CompressionResult con bits y métricas.

        Raises:
            KeyError: si algún símbolo no está en el codebook.
        """
        if not symbols:
            raise ValueError("La lista de símbolos está vacía.")

        bits_parts: list[str] = []
        for sym in symbols:
            if sym not in codebook.table:
                raise KeyError(f"Símbolo '{sym}' no encontrado en el codebook.")
            bits_parts.append(codebook.table[sym])

        bits = "".join(bits_parts)

        alphabet_size = len(codebook.table)
        bits_per_sym  = max(1, alphabet_size.bit_length())
        original_bits = len(symbols) * bits_per_sym
        compressed    = len(bits)

        return CompressionResult(
            bits              = bits,
            codebook          = codebook,
            original_bits     = original_bits,
            compressed_bits   = compressed,
            compression_ratio = self.compression_ratio(original_bits, compressed),
            efficiency        = None,
        )

    # ── decode ─────────────────────────────────────────────────────────────

    def decode(self, bits: str, codebook: Codebook) -> list[Any]:
        """
        Decodifica la cadena de bits usando la tabla inversa (prefijo libre).

        Args:
            bits    : cadena de bits.
            codebook: el mismo codebook usado en encode().

        Returns:
            Lista de símbolos reconstruidos.

        Raises:
            ValueError: si hay bits sobrantes que no coinciden con ningún código.
        """
        if not bits:
            raise ValueError("La cadena de bits está vacía.")

        symbols: list[Any] = []
        current = ""
        for bit in bits:
            current += bit
            if current in codebook.inverse:
                symbols.append(codebook.inverse[current])
                current = ""

        if current:
            raise ValueError(
                f"Bits sobrantes sin decodificar: '{current}'. "
                f"El codebook puede no coincidir con la secuencia codificada."
            )

        return symbols

    # ── Partición recursiva privada ────────────────────────────────────────

    def _split(
        self,
        items: list[tuple[Any, float]],
        table: dict[Any, str],
    ) -> None:
        """
        Divide recursivamente la lista de (símbolo, prob) en dos grupos
        y asigna prefijos '0'/'1'.

        Args:
            items: sublista de símbolos con probabilidades (ordenados desc).
            table: diccionario de códigos que se va completando in-place.
        """
        if len(items) <= 1:
            return

        # Encontrar el punto de corte que minimiza la diferencia de probabilidades
        total      = sum(p for _, p in items)
        cumulative = 0.0
        best_split = 1
        best_diff  = float('inf')

        for i in range(1, len(items)):
            cumulative += items[i - 1][1]
            diff = abs(2 * cumulative - total)
            if diff < best_diff:
                best_diff  = diff
                best_split = i

        upper = items[:best_split]
        lower = items[best_split:]

        # Asignar prefijos
        for sym, _ in upper:
            table[sym] += "0"
        for sym, _ in lower:
            table[sym] += "1"

        # Recursión en cada grupo
        self._split(upper, table)
        self._split(lower, table)
