"""
ImageReader
Lee una imagen PNG/JPG y la convierte en una secuencia de bytes (píxeles),
tratando cada byte como un símbolo de la fuente.

Dependencias : Pillow

Uso:
    reader = ImageReader(mode='L')      # escala de grises (1 byte/píxel)
    stats  = reader.read("foto.png")
    syms   = reader.to_symbols("foto.png")  # [120, 200, 34, ...]
"""

from __future__ import annotations
import os
from .base import SourceReader, SourceStats


class ImageReader(SourceReader):
    """
    Lee una imagen y trata cada byte de píxel como un símbolo.

    Args:
        mode   : modo de conversión de imagen.
                 'L'   → escala de grises, 1 byte por píxel (recomendado, alfabeto de 256 símbolos).
                 'RGB' → color, 3 bytes por píxel (alfabeto de 0–255 por canal).
                 '1'   → binario, 1 bit por píxel (alfabeto {0, 1}).
        max_pixels: límite de píxeles a leer (None = sin límite).
                    Útil para pruebas rápidas con imágenes grandes.
    """

    SUPPORTED_MODES = ('L', 'RGB', '1')

    def __init__(self, mode: str = 'L', max_pixels: int | None = None) -> None:
        if mode not in self.SUPPORTED_MODES:
            raise ValueError(f"mode debe ser uno de {self.SUPPORTED_MODES}, recibió '{mode}'.")
        self._mode       = mode
        self._max_pixels = max_pixels

    # ── Implementación de la interfaz ──────────────────────────────────────

    def read(self, source: str) -> SourceStats:
        """
        Lee la imagen desde disco y calcula estadísticas de sus bytes.

        Args:
            source: ruta al archivo de imagen (str).

        Returns:
            SourceStats con los bytes de píxel como símbolos.

        Raises:
            FileNotFoundError: si la ruta no existe.
            ValueError       : si la imagen no tiene píxeles válidos.
            ImportError      : si Pillow no está instalado.
        """
        symbols = self.to_symbols(source)
        probs   = self.compute_probabilities(symbols)
        entropy = self.compute_entropy(probs)

        # Metadatos de la imagen
        width, height = self._get_dimensions(source)

        return SourceStats(
            symbols       = symbols,
            alphabet      = set(symbols),
            probabilities = probs,
            entropy       = entropy,
            metadata      = {
                "source_type"  : "image",
                "path"         : source,
                "mode"         : self._mode,
                "width"        : width,
                "height"       : height,
                "total_pixels" : width * height,
                "symbols_read" : len(symbols),
                "alphabet_size": len(probs),
            },
        )

    def to_symbols(self, source: str) -> list[int]:
        """
        Carga la imagen y extrae los bytes de píxel como lista de enteros.

        Args:
            source: ruta al archivo de imagen.

        Returns:
            Lista de enteros (0–255 para 'L'; tuplas (R,G,B) para 'RGB'; 0/1 para '1').
        """
        try:
            from PIL import Image
        except ImportError as e:
            raise ImportError("Pillow es necesario para ImageReader. Instala con: pip install Pillow") from e

        if not os.path.exists(source):
            raise FileNotFoundError(f"No se encontró la imagen: '{source}'")

        img  = Image.open(source).convert(self._mode)
        data = list(img.getdata())

        if not data:
            raise ValueError(f"La imagen '{source}' no contiene datos de píxel.")

        if self._max_pixels is not None:
            data = data[: self._max_pixels]

        # Para RGB, aplanar tuplas a bytes individuales
        if self._mode == 'RGB':
            flat: list[int] = []
            for pixel in data:
                flat.extend(pixel)          # (R, G, B) → 3 enteros
            return flat

        return [int(p) for p in data]

    # ── Utilidad privada ───────────────────────────────────────────────────

    def _get_dimensions(self, path: str) -> tuple[int, int]:
        """Devuelve (ancho, alto) de la imagen sin recargarla completamente."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                return img.size          # (width, height)
        except Exception:
            return (0, 0)
