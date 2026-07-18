"""
M3 — channel
Exporta todas las implementaciones del módulo de canal.
"""

from .base          import Channel, TransmissionResult
from .bsc           import BSChannel

__all__ = [
    "Channel",
    "TransmissionResult",
    "BSChannel"
]