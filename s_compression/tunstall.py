"""
TunstallCodec
Implementación de la codificación de Tunstall.

Asigna códigos de longitud FIJA (k bits) a frases de longitud VARIABLE,
expandiendo greedy el árbol hasta llenar el diccionario de 2^k entradas.
A diferencia de Huffman/Shannon-Fano, el decoder es un simple lookup O(1).

Uso:
    codec    = TunstallCodec(k=3)
    codebook = codec.build_codebook({'A': 0.7, 'B': 0.3})
    result   = codec.encode(['A','A','B','A','A','A','B'], codebook)
    symbols  = codec.decode(result.bits, codebook)

    # Métricas del analizador
    print(codec.phrase_length_distribution(codebook))
"""

from __future__ import annotations
import heapq
from math import log2
from typing import Any

from .base import SourceCodec, Codebook, CompressionResult


class TunstallCodec(SourceCodec):
    """
    Codificador/Decodificador Tunstall.

    Args:
        k: número de bits por código (tamaño fijo del codeword).
           El diccionario tendrá hasta 2^k entradas.
           Debe satisfacer: 2^k ≥ |alfabeto|.
    """

    def __init__(self, k: int = 3) -> None:
        if k < 1:
            raise ValueError("k debe ser al menos 1.")
        self.k = k

    # ── build_codebook ─────────────────────────────────────────────────────

    def build_codebook(self, probabilities: dict[Any, float]) -> Codebook:
        """
        Construye el diccionario Tunstall expandiendo frases greedy.

        Algoritmo:
            1. Inicializar hojas con los símbolos del alfabeto.
            2. Mientras (|hojas| + |A| − 1) ≤ 2^k:
               a. Sacar la hoja de mayor probabilidad.
               b. Expandirla: crear |A| hijos (frase + símbolo).
            3. Asignar código binario de k bits a cada hoja final.

        Args:
            probabilities: mapping símbolo → P(símbolo).

        Returns:
            Codebook con table (frase→código), inverse (código→frase),
            avg_length (L̄) y code_length = k.

        Raises:
            ValueError: si k es demasiado pequeño para el alfabeto.
        """
        self.validate_probabilities(probabilities)
        alphabet = list(probabilities.keys())

        if len(alphabet) < 2:
            raise ValueError("Tunstall requiere al menos 2 símbolos distintos.")

        max_leaves = 2 ** self.k
        if max_leaves < len(alphabet):
            min_k = (len(alphabet) - 1).bit_length()
            raise ValueError(
                f"k={self.k} es insuficiente para {len(alphabet)} símbolos. "
                f"Usa k ≥ {min_k}."
            )

        # Min-heap: (-prob, frase) — negamos para que heapq se comporte como max-heap
        leaves: list[tuple[float, str]] = [
            (-probabilities[s], str(s)) for s in alphabet
        ]
        heapq.heapify(leaves)

        # Expansión greedy
        while True:
            # Si expandir la hoja de mayor prob excede el límite, parar
            if len(leaves) + len(alphabet) - 1 > max_leaves:
                break

            neg_p, phrase = heapq.heappop(leaves)
            p = -neg_p

            for sym in alphabet:
                child_p    = p * probabilities[sym]
                child_phrase = phrase + str(sym)
                heapq.heappush(leaves, (-child_p, child_phrase))

        # Ordenar hojas de mayor a menor probabilidad para asignación determinista
        leaves.sort(key=lambda x: x[0])   # más negativo = mayor prob → primero

        # Asignar códigos de k bits
        table:   dict[str, str] = {}
        inverse: dict[str, str] = {}
        for i, (neg_p, phrase) in enumerate(leaves):
            code           = format(i, f'0{self.k}b')
            table[phrase]  = code
            inverse[code]  = phrase

        # Calcular L̄ = longitud media de frase ponderada por prob normalizada
        total_prob = sum(-neg_p for neg_p, _ in leaves)
        avg_length = sum(
            len(phrase) * (-neg_p) / total_prob
            for neg_p, phrase in leaves
        )

        return Codebook(
            table       = table,
            inverse     = inverse,
            avg_length  = avg_length,
            code_length = self.k,
        )

    # ── encode ─────────────────────────────────────────────────────────────

    def encode(self, symbols: list[Any], codebook: Codebook) -> CompressionResult:
        """
        Codifica la secuencia de símbolos buscando la frase más larga (greedy).

        Args:
            symbols : lista de símbolos de la fuente.
            codebook: construido con build_codebook().

        Returns:
            CompressionResult con bits de longitud fija (múltiplo de k).

        Raises:
            ValueError: si ninguna frase del diccionario coincide en alguna posición.
        """
        if not symbols:
            raise ValueError("La lista de símbolos está vacía.")

        text = "".join(str(s) for s in symbols)

        # Ordenar frases de más larga a más corta (greedy match)
        phrases_sorted = sorted(codebook.table.keys(), key=len, reverse=True)

        bits_parts: list[str] = []
        i = 0
        while i < len(text):
            matched = False
            for phrase in phrases_sorted:
                if text[i: i + len(phrase)] == phrase:
                    bits_parts.append(codebook.table[phrase])
                    i += len(phrase)
                    matched = True
                    break
            if not matched:
                raise ValueError(
                    f"No se encontró frase en el diccionario para la posición {i} "
                    f"(símbolo '{text[i]}'). ¿El símbolo está en el alfabeto?"
                )

        bits = "".join(bits_parts)

        # bits originales: ceil(log2(|A|)) bits/símbolo (codificación uniforme)
        alphabet_size = len(set(symbols))
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
        Decodifica la cadena de bits en bloques de k bits (lookup O(1)).

        Args:
            bits    : cadena de bits (longitud múltiplo de k).
            codebook: el mismo codebook usado en encode().

        Returns:
            Lista de símbolos reconstruidos (puede incluir el último símbolo
            del padding del encoder si se usó).

        Raises:
            ValueError: si la longitud de bits no es múltiplo de k,
                        o si algún bloque no está en el diccionario.
        """
        if not bits:
            raise ValueError("La cadena de bits está vacía.")

        k = codebook.code_length
        if k is None:
            raise ValueError("Este codebook no tiene code_length definido (no es Tunstall).")
        if len(bits) % k != 0:
            raise ValueError(
                f"La longitud de bits ({len(bits)}) no es múltiplo de k={k}. "
                f"Los bits pueden estar truncados."
            )

        symbols: list[Any] = []
        for i in range(0, len(bits), k):
            block = bits[i: i + k]
            if block not in codebook.inverse:
                raise ValueError(
                    f"Bloque '{block}' en posición {i} no está en el diccionario. "
                    f"¿El codebook coincide con la codificación original?"
                )
            phrase = codebook.inverse[block]
            symbols.extend(list(phrase))

        return symbols

    # ── compute_efficiency (override para Tunstall) ────────────────────────

    def compute_efficiency(self, avg_length: float, entropy: float) -> float:
        """
        Eficiencia de Tunstall = (k / L̄) / H(X).
        Sobreescribe la fórmula general de SourceCodec.

        Args:
            avg_length: L̄ en símbolos/frase.
            entropy   : H(X) en bits/símbolo.

        Returns:
            Eficiencia entre 0 y 1.
        """
        if avg_length <= 0:
            raise ValueError("avg_length debe ser positivo.")
        if entropy <= 0:
            return 0.0
        rate = self.k / avg_length       # bits/símbolo de la tasa Tunstall
        return rate / entropy

    # ── Utilidades de análisis ─────────────────────────────────────────────

    def phrase_length_distribution(self, codebook: Codebook) -> dict[int, int]:
        """
        Cuenta cuántas frases hay de cada longitud en el diccionario.

        Returns:
            {longitud: cantidad_de_frases}  — útil para el analizador.
        """
        dist: dict[int, int] = {}
        for phrase in codebook.table:
            l = len(phrase)
            dist[l] = dist.get(l, 0) + 1
        return dict(sorted(dist.items()))

    def tunstall_rate(self, codebook: Codebook) -> float:
        """
        Tasa de Tunstall = k / L̄  en bits por símbolo fuente.
        """
        if codebook.avg_length <= 0:
            return 0.0
        return self.k / codebook.avg_length
