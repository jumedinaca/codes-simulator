"""
BSChannel — Canal Binario Simétrico (Binary Symmetric Channel)

Cada bit se invierte independientemente con probabilidad p.
Modelo más simple y fundamental en teoría de la información.

Propiedades:
    Capacidad: C = 1 − H(p) = 1 + p·log₂(p) + (1−p)·log₂(1−p)
    Crossover prob: P(error) = p  (simétrico: mismo p para 0→1 y 1→0)
"""
from __future__ import annotations
import random
from math import log2
from .base import Channel, TransmissionResult


class BSChannel(Channel):
    """
    Canal Binario Simétrico.

    Args:
        p   : probabilidad de error de bit  (0 ≤ p ≤ 0.5)
        seed: semilla para reproducibilidad (None = aleatorio)
    """

    def __init__(self, p: float = 0.05, seed: int | None = None) -> None:
        self._validate_p(p)
        self.p    = p
        self._rng = random.Random(seed)

    # ── Interfaz Channel ───────────────────────────────────────────────────

    def transmit(self, bits: str) -> TransmissionResult:
        """
        Envía bits por el canal BSC, flipeando cada bit con prob p.

        Returns:
            TransmissionResult con bits recibidos, máscara de error y BER.
        """
        self.validate_bits(bits)

        received = []
        for bit in bits:
            if self._rng.random() < self.p:
                received.append('1' if bit == '0' else '0')   # flip
            else:
                received.append(bit)

        received_str = ''.join(received)
        mask   = self.compute_error_mask(bits, received_str)
        errors = mask.count('1')
        ber    = errors / len(bits)

        return TransmissionResult(
            sent       = bits,
            received   = received_str,
            error_mask = mask,
            bit_errors = errors,
            ber        = ber,
            capacity   = self.capacity(),
            params     = {'p': self.p},
        )

    def capacity(self) -> float:
        """
        C = 1 − H(p)  donde H(p) = −p·log₂p − (1−p)·log₂(1−p)

        Returns:
            Capacidad en bits/uso. 1.0 cuando p=0, 0.0 cuando p=0.5.
        """
        if self.p == 0:
            return 1.0
        if self.p == 0.5:
            return 0.0
        q = 1 - self.p
        h = -self.p * log2(self.p) - q * log2(q)   # H(p)
        return max(0.0, 1.0 - h)

    def set_params(self, **kwargs) -> None:
        """
        Actualiza parámetros del canal sin crear nueva instancia.
        Acepta: p (float)
        """
        if 'p' in kwargs:
            self._validate_p(kwargs['p'])
            self.p = kwargs['p']

    # ── Utilidad privada ───────────────────────────────────────────────────

    @staticmethod
    def _validate_p(p: float) -> None:
        if not (0.0 <= p <= 0.5):
            raise ValueError(f"p debe estar en [0, 0.5], recibido: {p}")