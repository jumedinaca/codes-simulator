"""
M1 — source
Exporta todas las implementaciones del módulo de fuente de información.
"""

from .source       import SourceReader, SourceStats

#Implementaciones
from .text_reader  import TextReader
from .image_reader import ImageReader
from .bits_reader  import BitsReader

__all__ = [
    "SourceReader",
    "SourceStats",
    "TextReader",
    "ImageReader",
    "BitsReader",
]
