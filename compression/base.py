"""
M2 — Codificación Fuente (Compresión)
======================================
Interfaz base para cualquier algoritmo de compresión sin pérdida.
Toda implementación concreta debe heredar de `SourceCodec`.

Implementaciones esperadas:
    HuffmanCodec     — codificación Huffman
    ShannonFanoCodec — codificación Shannon-Fano
    TunstallCodec    — codificación Tunstall (longitud fija, frases variables)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


# ── Tipos de salida ────────────────────────────────────────────────────────

@dataclass
class Codebook:
    """
    Diccionario de codificación generado por el algoritmo.

    Attributes:
        table        : mapping  frase/símbolo → código binario (str de '0'/'1')
        inverse      : mapping  código binario → frase/símbolo (para decodificar)
        avg_length   : longitud media de código L̄  (bits / símbolo fuente)
        code_length  : longitud fija del código si aplica (Tunstall), None si variable
    """
    table:       dict[Any, str]
    inverse:     dict[str, Any]
    avg_length:  float
    code_length: int | None = None          # solo Tunstall y similares


@dataclass
class CompressionResult:
    """
    Resultado de codificar una secuencia de símbolos.

    Attributes:
        bits            : cadena de bits resultante ('010110...')
        codebook        : diccionario usado para la codificación
        original_bits   : longitud en bits de la fuente sin comprimir
        compressed_bits : longitud en bits tras comprimir
        compression_ratio: original_bits / compressed_bits
        efficiency      : L̄ / H(X) — qué tan cerca del límite de Shannon
                          (se completa externamente con la entropía de M1)
    """
    bits:             str
    codebook:         Codebook
    original_bits:    int
    compressed_bits:  int
    compression_ratio: float
    efficiency:       float | None = None   # se rellena desde el pipeline


# ── Interfaz principal ─────────────────────────────────────────────────────

class SourceCodec(ABC):
    """
    Interfaz que debe implementar todo algoritmo de compresión fuente.

    Flujo de uso:
        codec  = ConcreteCodec(...)
        cb     = codec.build_codebook(probs)   # entrenar con probabilidades
        result = codec.encode(symbols, cb)      # comprimir
        syms   = codec.decode(result.bits, cb)  # descomprimir
    """

    @abstractmethod
    def build_codebook(self, probabilities: dict[Any, float]) -> Codebook:
        """
        Construye el diccionario de codificación a partir de las probabilidades
        de la fuente entregadas por M1.

        Args:
            probabilities: mapping símbolo → P(símbolo),  Σ = 1.0
                           Ejemplo: {'A': 0.5, 'B': 0.3, 'C': 0.2}

        Returns:
            Codebook con tabla directa e inversa ya construidas.

        Raises:
            ValueError: si probabilities está vacío o no suma ~1.0.
        """

    @abstractmethod
    def encode(self, symbols: list[Any], codebook: Codebook) -> CompressionResult:
        """
        Codifica una secuencia de símbolos usando el codebook dado.

        Args:
            symbols : lista de símbolos de la fuente (salida de M1.to_symbols)
            codebook: diccionario construido con build_codebook()

        Returns:
            CompressionResult con la cadena de bits y métricas.

        Raises:
            KeyError: si algún símbolo no está en el codebook.
        """

    @abstractmethod
    def decode(self, bits: str, codebook: Codebook) -> list[Any]:
        """
        Reconstruye la secuencia original de símbolos a partir de los bits.

        Args:
            bits    : cadena de bits ('010110...')
            codebook: el mismo codebook usado en encode()

        Returns:
            Lista de símbolos reconstruidos.

        Raises:
            ValueError: si los bits no corresponden a ninguna entrada del codebook.
        """

    # ── Métodos utilitarios con implementación por defecto ─────────────────

    def compute_efficiency(self, avg_length: float, entropy: float) -> float:
        """
        Eficiencia = H(X) / L̄  (entre 0 y 1, idealmente cerca de 1).
        Para Tunstall: eficiencia = (k / L̄) / H(X).

        Args:
            avg_length: L̄ en bits/símbolo
            entropy   : H(X) en bits/símbolo (proveniente de M1)
        """
        if avg_length <= 0:
            raise ValueError("avg_length debe ser positivo.")
        if entropy <= 0:
            return 0.0
        return entropy / avg_length

    def compression_ratio(self, original_bits: int, compressed_bits: int) -> float:
        """
        Tasa de compresión = bits originales / bits comprimidos.
        Valor > 1 indica compresión efectiva.
        """
        if compressed_bits <= 0:
            raise ValueError("compressed_bits debe ser positivo.")
        return original_bits / compressed_bits

    def validate_probabilities(self, probabilities: dict[Any, float]) -> None:
        """
        Verifica que las probabilidades sean válidas (positivas y suman ~1.0).
        Las subclases pueden llamar esto al inicio de build_codebook().
        """
        if not probabilities:
            raise ValueError("El diccionario de probabilidades está vacío.")
        total = sum(probabilities.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Las probabilidades deben sumar 1.0, suman {total:.4f}.")
        if any(p < 0 for p in probabilities.values()):
            raise ValueError("Todas las probabilidades deben ser no negativas.")
