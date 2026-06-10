"""
TextReader
Lee texto plano UTF-8 y produce SourceStats con probabilidades de caracteres.

Uso:
    reader = TextReader()
    stats  = reader.read("AABBAAC")
    syms   = reader.to_symbols("AABBAAC")  # ['A','A','B','B','A','A','C']
"""

from __future__ import annotations
from .base import SourceReader, SourceStats


class TextReader(SourceReader):
    """
    Lee texto plano (str) y trata cada carácter como un símbolo.

    Args:
        lowercase: si True, convierte todo a minúsculas antes de procesar.
                   Reduce el tamaño del alfabeto en textos naturales.
    """

    def __init__(self, lowercase: bool = False) -> None:
        self._lowercase = lowercase

    # ── Implementación de la interfaz ──────────────────────────────────────

    def read(self, source: str) -> SourceStats:
        """
        Lee el texto y calcula frecuencias, probabilidades y entropía.

        Args:
            source: cadena de texto plano (str).

        Returns:
            SourceStats con símbolos, probabilidades y H(X).

        Raises:
            ValueError: si source está vacío.
            TypeError : si source no es str.
        """
        if not isinstance(source, str):
            raise TypeError(f"TextReader espera str, recibió {type(source).__name__}.")
        if not source:
            raise ValueError("El texto de entrada está vacío.")

        text    = source.lower() if self._lowercase else source
        symbols = list(text)

        probs   = self.compute_probabilities(symbols)
        entropy = self.compute_entropy(probs)

        return SourceStats(
            symbols       = symbols,
            alphabet      = set(symbols),
            probabilities = probs,
            entropy       = entropy,
            metadata      = {
                "source_type" : "text",
                "length"      : len(symbols),
                "alphabet_size": len(probs),
                "lowercase"   : self._lowercase,
            },
        )

    def to_symbols(self, source: str) -> list[str]:
        """
        Convierte el texto en lista de caracteres (sin calcular métricas).

        Args:
            source: cadena de texto plano.

        Returns:
            Lista de caracteres.
        """
        if not isinstance(source, str):
            raise TypeError(f"TextReader espera str, recibió {type(source).__name__}.")
        if not source:
            raise ValueError("El texto de entrada está vacío.")
        text = source.lower() if self._lowercase else source
        return list(text)
