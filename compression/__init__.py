"""
M2 — compression
Exporta todas las implementaciones del módulo de codificación fuente.
"""

from .base          import SourceCodec, Codebook, CompressionResult
from .huffman       import HuffmanCodec
from .shannon_fano  import ShannonFanoCodec
from .tunstall      import TunstallCodec

__all__ = [
    "SourceCodec",
    "Codebook",
    "CompressionResult",
    "HuffmanCodec",
    "ShannonFanoCodec",
    "TunstallCodec",
]
