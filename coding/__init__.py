"""
M4 — Correcion de errores
Exporta todas las implementaciones del módulo de correccion de errores.
"""

from .base import ErrorCorrectingCode, EncodedBlock, DecodedBlock, CodingStats

from .hamming import HammingCode

__all__ = [
    "ErrorCorrectingCode",
    "EncodedBlock",
    "DecodedBlock",
    "CodingStats",
    "HammingCode"
]