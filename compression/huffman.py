"""
HuffmanCodec
Implementación de la codificación de Huffman.

Construye el árbol óptimo de prefijos y asigna códigos de longitud variable
minimizando la longitud media L̄. Garantiza L̄ ≤ H(X) + 1.

Uso:
    codec    = HuffmanCodec()
    codebook = codec.build_codebook({'A': 0.5, 'B': 0.3, 'C': 0.2})
    result   = codec.encode(['A', 'B', 'A', 'C'], codebook)
    symbols  = codec.decode(result.bits, codebook)
"""

from __future__ import annotations
import heapq
from math import log2
from typing import Any

from .base import SourceCodec, Codebook, CompressionResult


# ── Nodo del árbol de Huffman ──────────────────────────────────────────────

class _HuffmanNode:
    """Nodo interno del árbol de Huffman."""

    # Forzamos los atributos
    __slots__ = ("symbol", "prob", "left", "right")

    def __init__(
        self,
        prob:   float,
        symbol: Any                  = None,
        left:   "_HuffmanNode | None" = None,
        right:  "_HuffmanNode | None" = None,
    ) -> None:
        self.symbol = symbol
        self.prob   = prob
        self.left   = left
        self.right  = right

    # heapq compara nodos; usamos (prob, contador) para evitar comparar symbols
    def __lt__(self, other: "_HuffmanNode") -> bool:
        return self.prob < other.prob


# ── Codec ──────────────────────────────────────────────────────────────────

class HuffmanCodec(SourceCodec):
    """
    Codificador/Decodificador Huffman.

    Guarda el árbol construido en `self.tree` para que el pipeline o el
    visualizador puedan acceder a él después de build_codebook().
    """

    def __init__(self) -> None:
        self.tree: _HuffmanNode | None = None   # raíz del árbol, disponible tras build

    # ── build_codebook ─────────────────────────────────────────────────────

    def build_codebook(self, probabilities: dict[Any, float]) -> Codebook:
        """
        Construye el árbol de Huffman y genera los códigos binarios.

        Algoritmo:
            1. Crear un nodo hoja por símbolo.
            2. Insertar todos en un min-heap por probabilidad.
            3. Mientras haya más de un nodo: sacar los dos de menor prob,
               crear un nodo interno con prob = suma, reinsertar.
            4. Recorrer el árbol asignando '0' a ramas izquierdas y '1' a derechas.

        Args:
            probabilities: {'A': 0.5, 'B': 0.3, 'C': 0.2}

        Returns:
            Codebook con tabla directa, inversa y L̄.

        Raises:
            ValueError: si hay menos de 2 símbolos.
        """
        self.validate_probabilities(probabilities)
        if len(probabilities) < 2:
            raise ValueError("Huffman requiere al menos 2 símbolos distintos.")

        # 1. Crear hojas y construir el heap
        heap: list[_HuffmanNode] = [
            _HuffmanNode(prob=p, symbol=s)
            for s, p in probabilities.items()
        ]
        heapq.heapify(heap)

        # 2. Construir el árbol
        counter = 0   # desempate determinístico
        while len(heap) > 1:
            left  = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = _HuffmanNode(
                prob  = left.prob + right.prob,
                left  = left,
                right = right,
            )
            heapq.heappush(heap, parent)
            counter += 1

        self.tree = heap[0]

        # 3. Recorrer el árbol y asignar códigos
        table: dict[Any, str] = {}
        self._assign_codes(self.tree, "", table)

        # 4. Calcular L̄ = Σ P(sᵢ) · len(code(sᵢ))
        avg_length = sum(
            probabilities[sym] * len(code)
            for sym, code in table.items()
        )

        inverse = {code: sym for sym, code in table.items()}

        return Codebook(
            table       = table,
            inverse     = inverse,
            avg_length  = avg_length,
            code_length = None,          # Huffman es longitud variable
        )

    # ── encode ─────────────────────────────────────────────────────────────

    def encode(self, symbols: list[Any], codebook: Codebook) -> CompressionResult:
        """
        Codifica la lista de símbolos concatenando sus códigos binarios.

        Args:
            symbols : lista de símbolos de la fuente.
            codebook: construido con build_codebook().

        Returns:
            CompressionResult con bits, ratio y métricas.

        Raises:
            KeyError: si algún símbolo no está en el codebook.
        """
        if not symbols:
            raise ValueError("La lista de símbolos está vacía.")

        bits_parts: list[str] = []
        for sym in symbols:
            if sym not in codebook.table:
                raise KeyError(
                    f"Símbolo '{sym}' no está en el codebook. "
                    f"Asegúrate de que build_codebook() se llamó con las mismas probabilidades."
                )
            bits_parts.append(codebook.table[sym])

        bits = "".join(bits_parts)

        # bits originales asumiendo log2(|A|) bits/símbolo (codificación uniforme)
        alphabet_size = len(codebook.table)
        bits_per_sym  = max(1, alphabet_size.bit_length())   # ceil(log2(|A|))
        original_bits = len(symbols) * bits_per_sym
        compressed    = len(bits)
        ratio         = self.compression_ratio(original_bits, compressed)

        return CompressionResult(
            bits              = bits,
            codebook          = codebook,
            original_bits     = original_bits,
            compressed_bits   = compressed,
            compression_ratio = ratio,
            efficiency        = None,    # se completa en el pipeline con H(X)
        )

    # ── decode ─────────────────────────────────────────────────────────────

    def decode(self, bits: str, codebook: Codebook) -> list[Any]:
        """
        Decodifica la cadena de bits reconstruyendo la secuencia de símbolos.
        Usa recorrido del árbol (prefijo libre → siempre decodificable sin ambigüedad).

        Args:
            bits    : cadena de bits ('010110...').
            codebook: el mismo codebook usado en encode().

        Returns:
            Lista de símbolos reconstruidos.

        Raises:
            ValueError: si los bits no forman ninguna secuencia válida.
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
                f"Bits sobrantes al final de la decodificación: '{current}'. "
                f"¿Los bits fueron truncados o el codebook no coincide?"
            )

        return symbols

    # ── Utilidad privada ───────────────────────────────────────────────────

    def _assign_codes(
        self,
        node:  _HuffmanNode,
        prefix: str,
        table:  dict[Any, str],
    ) -> None:
        """Recorre el árbol en profundidad asignando prefijos binarios."""
        if node.symbol is not None:
            # Hoja: asignar código (caso especial: un solo símbolo → '0')
            table[node.symbol] = prefix if prefix else "0"
            return
        if node.left:
            self._assign_codes(node.left,  prefix + "0", table)
        if node.right:
            self._assign_codes(node.right, prefix + "1", table)
