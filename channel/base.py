"""
M3 — Canal de Comunicación

Interfaz base para cualquier modelo de canal ruidoso.
Toda implementación concreta debe heredar de `Channel`.

Implementaciones:
    BSChannel   — Canal Binario Simétrico (Binary Symmetric Channel)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Tipos de salida ────────────────────────────────────────────────────────

@dataclass
class TransmissionResult:
    """
    Resultado de transmitir bits a través del canal.

    Attributes:
        sent        : bits enviados (cadena '010110...')
        received    : bits recibidos con errores introducidos
        error_mask  : máscara de errores — '1' en posiciones donde hubo flip
        bit_errors  : número total de bits corrompidos
        ber         : Bit Error Rate = bit_errors / len(sent)
        capacity    : capacidad del canal C en bits/uso (depende del modelo)
        params      : parámetros del canal usados en esta transmisión
                      (ej. {'p': 0.05} para BSC)
    """
    sent:       str
    received:   str
    error_mask: str
    bit_errors: int
    ber:        float
    capacity:   float
    params:     dict[str, Any] = field(default_factory=dict)


# ── Interfaz principal ─────────────────────────────────────────────────────

class Channel(ABC):
    """
    Interfaz que debe implementar todo modelo de canal del simulador.

    Flujo de uso:
        channel = ConcreteChannel(p=0.05, seed=42)
        result  = channel.transmit(bits)
        c       = channel.capacity()
    """

    @abstractmethod
    def transmit(self, bits: str) -> TransmissionResult:
        """
        Transmite una cadena de bits a través del canal e introduce errores.

        Args:
            bits: cadena de bits a enviar ('010110...')
                  Proveniente de M2.encode() o M4.encode() según el pipeline.

        Returns:
            TransmissionResult con los bits recibidos y métricas de error.

        Raises:
            ValueError: si bits está vacío o contiene caracteres distintos a '0'/'1'.
        """

    @abstractmethod
    def capacity(self) -> float:
        """
        Calcula la capacidad del canal C en bits por uso.

        Para BSC:  C = 1 − H(p) = 1 + p·log₂p + (1−p)·log₂(1−p)
        Para AWGN: C = ½·log₂(1 + SNR)

        Returns:
            Capacidad en bits/uso. Valor entre 0 (canal inútil) y 1 (canal perfecto).
        """

    @abstractmethod
    def set_params(self, **kwargs: Any) -> None:
        """
        Actualiza los parámetros del canal sin crear una nueva instancia.
        Permite variar `p` en un bucle de simulación sin overhead.

        Args:
            **kwargs: parámetros específicos del canal.
                      BSC  → p (float): probabilidad de error de bit
                      AWGN → snr_db (float): relación señal-ruido en dB

        Raises:
            ValueError: si algún parámetro está fuera de su rango válido.
        """

    # ── Métodos utilitarios con implementación por defecto ─────────────────

    def validate_bits(self, bits: str) -> None:
        """
        Verifica que la cadena de bits sea válida.
        Las subclases deben llamar esto al inicio de transmit().
        """
        if not bits:
            raise ValueError("La cadena de bits está vacía.")
        invalid = set(bits) - {'0', '1'}
        if invalid:
            raise ValueError(f"Caracteres inválidos en bits: {invalid}")

    def compute_ber(self, sent: str, received: str) -> float:
        """
        BER = número de bits distintos / longitud total.

        Args:
            sent    : bits enviados
            received: bits recibidos

        Returns:
            BER entre 0.0 (sin errores) y 1.0 (todos erróneos).
        """
        if len(sent) != len(received):
            raise ValueError("sent y received deben tener la misma longitud.")
        errors = sum(s != r for s, r in zip(sent, received))
        return errors / len(sent)

    def compute_error_mask(self, sent: str, received: str) -> str:
        """
        Genera la máscara XOR entre sent y received.
        Un '1' en la posición i indica que el bit i fue corrompido.
        """
        if len(sent) != len(received):
            raise ValueError("sent y received deben tener la misma longitud.")
        return ''.join('1' if s != r else '0' for s, r in zip(sent, received))
