"""
M1 — Fuente de Información
==========================
Interfaz base para cualquier lector de fuente.
Toda implementación concreta debe heredar de `SourceReader`.

Implementaciones esperadas:
    TextReader   — lee texto plano UTF-8
    ImageReader  — lee imagen PNG/JPG como secuencia de bytes
    BitsReader   — lee secuencia binaria cruda
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Tipos de salida ────────────────────────────────────────────────────────

@dataclass
class SourceStats:
    """
    Resultado del análisis de una fuente.

    Attributes:
        symbols     : secuencia de símbolos leídos (ej. lista de chars o bytes)
        alphabet    : conjunto de símbolos únicos presentes
        probabilities: mapping símbolo → probabilidad  (Σ = 1.0)
        entropy     : H(X) en bits/símbolo
        metadata    : información adicional dependiente del tipo de fuente
                      (ej. {'encoding': 'utf-8', 'length': 240})
    """
    symbols:       list[Any]
    alphabet:      set[Any]
    probabilities: dict[Any, float]
    entropy:       float
    metadata:      dict[str, Any] = field(default_factory=dict)


# ── Interfaz principal ─────────────────────────────────────────────────────

class SourceReader(ABC):
    """
    Interfaz que debe implementar toda fuente de información del simulador.

    Flujo de uso:
        reader = ConcreteReader(...)
        stats  = reader.read(source)        # análisis completo
        syms   = reader.to_symbols(source)  # solo los símbolos, sin métricas
    """

    @abstractmethod
    def read(self, source: Any) -> SourceStats:
        """
        Lee la fuente y devuelve estadísticas completas.

        Args:
            source: recurso a leer. El tipo depende de la implementación:
                    - TextReader  → str  (texto plano)
                    - ImageReader → str  (ruta al archivo)
                    - BitsReader  → str  (cadena '010110...')

        Returns:
            SourceStats con probabilidades y entropía calculadas.

        Raises:
            ValueError: si la fuente está vacía o tiene formato inválido.
            FileNotFoundError: si la fuente es una ruta inexistente.
        """

    @abstractmethod
    def to_symbols(self, source: Any) -> list[Any]:
        """
        Convierte la fuente en una lista plana de símbolos sin calcular métricas.
        Útil cuando las probabilidades ya se conocen de antemano.

        Args:
            source: mismo tipo que en `read()`.

        Returns:
            Lista ordenada de símbolos (puede contener repetidos).
        """

    # ── Métodos utilitarios con implementación por defecto ─────────────────

    def compute_probabilities(self, symbols: list[Any]) -> dict[Any, float]:
        """
        Calcula P(sᵢ) = freq(sᵢ) / N a partir de una lista de símbolos.
        Las subclases pueden sobreescribir esto si tienen una fuente de
        probabilidades más precisa (ej. tabla de frecuencias del idioma).
        """
        if not symbols:
            raise ValueError("La lista de símbolos está vacía.")
        n = len(symbols)
        freq: dict[Any, int] = {}
        for s in symbols:
            freq[s] = freq.get(s, 0) + 1
        return {s: c / n for s, c in freq.items()}

    def compute_entropy(self, probabilities: dict[Any, float]) -> float:
        """
        H(X) = −Σ p(sᵢ) · log₂ p(sᵢ)

        Returns:
            Entropía en bits/símbolo. Retorna 0.0 para alfabeto de un símbolo.
        """
        from math import log2
        return -sum(p * log2(p) for p in probabilities.values() if p > 0)
