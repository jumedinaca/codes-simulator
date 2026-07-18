"""
M4 — Corrección de Errores

Interfaz base para cualquier código detector/corrector de errores.
Toda implementación concreta debe heredar de `ErrorCorrectingCode`.

Implementaciones:
    HammingCode      — Hamming(7,4): corrige 1 error, detecta 2
    ReedSolomonCode  — Reed-Solomon: ideal para ráfagas de errores
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Tipos de salida ────────────────────────────────────────────────────────

@dataclass
class EncodedBlock:
    """
    Resultado de codificar un bloque de datos con el código corrector.

    Attributes:
        data_bits     : bits de datos originales (sin redundancia)
        codeword_bits : palabra código = datos + bits de paridad/redundancia
        block_size    : tamaño del bloque de datos en bits  (k)
        codeword_size : tamaño de la palabra código en bits (n)
        rate          : tasa del código = k / n
    """
    data_bits:     str
    codeword_bits: str
    block_size:    int
    codeword_size: int
    rate:          float


@dataclass
class DecodedBlock:
    """
    Resultado de decodificar y corregir un bloque recibido.

    Attributes:
        received_bits  : bits recibidos del canal (con posibles errores)
        corrected_bits : bits tras aplicar corrección
        data_bits      : bits de datos extraídos (sin redundancia)
        syndrome       : síndrome calculado ('0...0' si no hay error)
        errors_detected: número de errores detectados
        errors_corrected: número de errores efectivamente corregidos
        success        : True si la corrección fue exitosa
        uncorrectable  : True si se detectaron más errores de los que el código puede corregir
    """
    received_bits:    str
    corrected_bits:   str
    data_bits:        str
    syndrome:         str
    errors_detected:  int
    errors_corrected: int
    success:          bool
    uncorrectable:    bool = False


@dataclass
class CodingStats:
    """
    Métricas agregadas del proceso de corrección sobre toda la transmisión.

    Attributes:
        ber_before      : BER antes de aplicar corrección (entrada del canal M3)
        ber_after       : BER después de aplicar corrección
        coding_gain_db  : ganancia de codificación = 10·log₁₀(BER_before / BER_after)
        total_blocks    : número de bloques procesados
        corrected_blocks: bloques en que se corrigió al menos un error
        failed_blocks   : bloques con errores no corregibles
    """
    ber_before:       float
    ber_after:        float
    coding_gain_db:   float
    total_blocks:     int
    corrected_blocks: int
    failed_blocks:    int


# ── Interfaz principal ─────────────────────────────────────────────────────

class ErrorCorrectingCode(ABC):
    """
    Interfaz que debe implementar todo código corrector de errores.

    Flujo de uso:
        code    = ConcreteCode(...)
        encoded = code.encode(data_bits)          # agregar redundancia
        # ... transmitir encoded.codeword_bits por M3 ...
        decoded = code.decode(received_bits)      # corregir y extraer datos
        stats   = code.evaluate(sent, received)   # métricas globales
    """

    # ── Propiedades que toda implementación debe exponer ───────────────────

    @property
    @abstractmethod
    def n(self) -> int:
        """Longitud de la palabra código (bits totales por bloque)."""

    @property
    @abstractmethod
    def k(self) -> int:
        """Longitud del mensaje de datos (bits de información por bloque)."""

    @property
    @abstractmethod
    def t(self) -> int:
        """Capacidad de corrección: número máximo de errores corregibles por bloque."""

    # ── Métodos principales ────────────────────────────────────────────────

    @abstractmethod
    def encode(self, data_bits: str) -> EncodedBlock:
        """
        Codifica una cadena de bits de datos agregando redundancia.

        El método debe:
        1. Dividir data_bits en bloques de k bits (padding si es necesario).
        2. Calcular los bits de paridad/redundancia para cada bloque.
        3. Concatenar todos los codewords en codeword_bits.

        Args:
            data_bits: cadena de bits de datos ('010110...')
                       Proveniente de M2.encode().bits

        Returns:
            EncodedBlock con el codeword completo listo para enviar por M3.

        Raises:
            ValueError: si data_bits está vacío o contiene caracteres inválidos.
        """

    @abstractmethod
    def decode(self, received_bits: str) -> DecodedBlock:
        """
        Decodifica y corrige errores en los bits recibidos del canal.

        El método debe:
        1. Dividir received_bits en bloques de n bits.
        2. Calcular el síndrome de cada bloque.
        3. Corregir errores si el síndrome indica error corregible.
        4. Extraer los k bits de datos de cada bloque corregido.

        Args:
            received_bits: bits recibidos del canal (salida de M3.transmit().received)
                           Debe tener longitud múltiplo de n.

        Returns:
            DecodedBlock con datos recuperados y métricas de corrección.

        Raises:
            ValueError: si received_bits no tiene longitud múltiplo de n.
        """

    @abstractmethod
    def syndrome(self, codeword_bits: str) -> str:
        """
        Calcula el síndrome de un codeword (un solo bloque de n bits).
        El síndrome es '0...0' si el codeword no tiene errores.

        Args:
            codeword_bits: cadena de n bits (un único bloque).

        Returns:
            Cadena de bits del síndrome (longitud n−k para Hamming).

        Raises:
            ValueError: si len(codeword_bits) != n.
        """

    @abstractmethod
    def evaluate(self, original_bits: str, decoded_bits: str, ber_before: float) -> CodingStats:
        """
        Calcula las métricas globales de corrección comparando la salida
        del decodificador con los datos originales.

        Args:
            original_bits: bits de datos originales antes de codificar (M2 output)
            decoded_bits  : bits recuperados tras decodificar (decode().data_bits)
            ber_before    : BER medido en M3 antes de la corrección

        Returns:
            CodingStats con BER antes/después, ganancia y conteos de bloques.
        """

    # ── Métodos utilitarios con implementación por defecto ─────────────────

    @property
    def rate(self) -> float:
        """Tasa del código R = k / n."""
        return self.k / self.n

    def pad_bits(self, bits: str, block_size: int, pad_char: str = '0') -> str:
        """
        Rellena bits con pad_char a la derecha hasta ser múltiplo de block_size.
        Las subclases deben usar esto en encode() para manejar el último bloque.
        """
        remainder = len(bits) % block_size
        if remainder:
            bits += pad_char * (block_size - remainder)
        return bits

    def split_blocks(self, bits: str, block_size: int) -> list[str]:
        """
        Divide una cadena de bits en bloques de block_size.
        Asume que len(bits) es múltiplo de block_size (usar pad_bits primero).
        """
        return [bits[i:i + block_size] for i in range(0, len(bits), block_size)]

    def compute_coding_gain(self, ber_before: float, ber_after: float) -> float:
        """
        Ganancia de codificación en dB = 10 · log₁₀(BER_before / BER_after).
        Retorna 0.0 si BER_after == 0 o BER_before == 0.
        """
        from math import log10
        if ber_before <= 0 or ber_after <= 0:
            return 0.0
        return 10 * log10(ber_before / ber_after)
