"""
BitsReader
Lee una secuencia binaria cruda ('010110...') y trata cada bit como símbolo.
"""

from __future__ import annotations
from .base import SourceReader, SourceStats


class BitsReader(SourceReader):
    """
    Lee secuencias de bits y las representa como símbolos '0' y '1'.

    El alfabeto siempre es {'0', '1'} aunque solo aparezca uno de los dos,
    ya que semánticamente es un canal binario.

    Args:
        force_binary: si True, garantiza que el diccionario de probabilidades
                      siempre contenga ambos símbolos ('0' y '1'), asignando
                      probabilidad 0.0 al símbolo ausente.
    """

    def __init__(self, force_binary: bool = True) -> None:
        self._force_binary = force_binary


    def read(self, source: str | list[int]) -> SourceStats:
        """
        Lee la secuencia de bits y calcula sus estadísticas.

        Args:
            source: cadena '010110...' o lista de enteros [0, 1, 0, 1, ...].

        Returns:
            SourceStats con símbolos '0'/'1', probabilidades y entropía.

        Raises:
            ValueError: si source está vacío o contiene caracteres distintos a 0/1.
            TypeError : si source no es str ni list.
        """
        symbols = self.to_symbols(source)
        probs   = self.compute_probabilities(symbols)

        if self._force_binary:
            # Asegurar que ambos símbolos estén presentes
            probs.setdefault('0', 0.0)
            probs.setdefault('1', 0.0)

        entropy = self.compute_entropy(probs)

        return SourceStats(
            symbols       = symbols,
            alphabet      = {'0', '1'} if self._force_binary else set(symbols),
            probabilities = probs,
            entropy       = entropy,
            metadata      = {
                "source_type"  : "bits",
                "length"       : len(symbols),
                "ones"         : symbols.count('1'),
                "zeros"        : symbols.count('0'),
                "ones_ratio"   : symbols.count('1') / len(symbols),
            },
        )

    def to_symbols(self, source: str | list[int]) -> list[str]:
        """
        Convierte la fuente en lista de caracteres '0' y '1'.

        Args:
            source: cadena '010110...' o lista [0, 1, 0, 1, ...].

        Returns:
            Lista de strings '0' o '1'.

        Raises:
            TypeError : si el tipo de source no es soportado.
            ValueError: si contiene valores distintos a 0/1.
        """
        if isinstance(source, str):
            raw = source
        elif isinstance(source, (list, tuple)):
            raw = ''.join(str(b) for b in source)
        else:
            raise TypeError(
                f"BitsReader espera str o list[int], recibió {type(source).__name__}."
            )

        if not raw:
            raise ValueError("La secuencia de bits está vacía.")

        invalid = set(raw) - {'0', '1'}
        if invalid:
            raise ValueError(
                f"La secuencia contiene caracteres inválidos: {invalid}. "
                f"Solo se permiten '0' y '1'."
            )

        return list(raw)
