"""
M5 — Métricas y Visualización
==============================
Interfaz base para recolectar, calcular y visualizar los resultados
del pipeline completo. Toda implementación concreta debe heredar de
`MetricsCollector` y/o `Visualizer` según su responsabilidad.

Implementaciones esperadas:
    PipelineMetrics   — agrega resultados de M1–M4 en un reporte unificado
    MatplotlibPlotter — genera gráficas BER vs p, histogramas, árbol Huffman/Tunstall
    StreamlitDashboard— interfaz web interactiva (hereda de Visualizer)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Importamos los tipos de resultado de los módulos anteriores
# (solo para type hints; no hay dependencia circular en runtime)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from source.base      import SourceStats
    from compression.base import CompressionResult
    from channel.base     import TransmissionResult
    from coding.base      import DecodedBlock, CodingStats


# ── Tipo unificado ─────────────────────────────────────────────────────────

@dataclass
class PipelineReport:
    """
    Reporte consolidado de una ejecución completa del pipeline M1→M5.
    Es el objeto que M5 construye y luego usa para graficar/exportar.

    Attributes:
        source_stats      : análisis de la fuente (M1)
        compression_result: resultado de la compresión (M2)
        codec_name        : nombre del algoritmo de compresión usado
        transmission      : resultado del canal (M3)
        channel_params    : parámetros del canal (ej. {'p': 0.05})
        decoded           : resultado de la corrección (M4), None si no se usa
        coding_stats      : métricas agregadas de M4, None si no se usa
        extra             : datos adicionales libres para extensiones futuras
    """
    source_stats:       SourceStats
    compression_result: CompressionResult
    codec_name:         str
    transmission:       TransmissionResult
    channel_params:     dict[str, Any]
    decoded:            DecodedBlock  | None = None
    coding_stats:       CodingStats   | None = None
    extra:              dict[str, Any] = field(default_factory=dict)


# ── Interfaz de recolección ────────────────────────────────────────────────

class MetricsCollector(ABC):
    """
    Responsable de agregar los resultados de cada módulo y calcular
    métricas derivadas que cruzan módulos (ej. eficiencia total del pipeline).

    Flujo de uso:
        collector = ConcreteCollector()
        collector.register_source(stats)
        collector.register_compression(result, codec_name='Tunstall')
        collector.register_transmission(trans_result)
        collector.register_correction(decoded, coding_stats)  # opcional
        report = collector.build_report()
    """

    @abstractmethod
    def register_source(self, stats: SourceStats) -> None:
        """
        Registra los resultados del módulo M1.

        Args:
            stats: SourceStats devuelto por SourceReader.read()
        """

    @abstractmethod
    def register_compression(self, result: CompressionResult, codec_name: str) -> None:
        """
        Registra los resultados del módulo M2 e indica qué algoritmo se usó.

        Args:
            result    : CompressionResult devuelto por SourceCodec.encode()
            codec_name: nombre legible del codec ('Huffman', 'Tunstall k=3', ...)
        """

    @abstractmethod
    def register_transmission(self, result: TransmissionResult) -> None:
        """
        Registra los resultados del módulo M3 (canal ruidoso).

        Args:
            result: TransmissionResult devuelto por Channel.transmit()
        """

    @abstractmethod
    def register_correction(self, decoded: DecodedBlock, stats: CodingStats) -> None:
        """
        Registra los resultados del módulo M4 (corrección de errores).
        Es opcional: no todos los escenarios usan corrección.

        Args:
            decoded: DecodedBlock devuelto por ErrorCorrectingCode.decode()
            stats  : CodingStats devuelto por ErrorCorrectingCode.evaluate()
        """

    @abstractmethod
    def build_report(self) -> PipelineReport:
        """
        Consolida todos los registros y calcula métricas derivadas.
        Debe llamarse después de registrar al menos M1, M2 y M3.

        Returns:
            PipelineReport con todos los datos del pipeline listos para M5.

        Raises:
            RuntimeError: si algún módulo obligatorio (M1, M2, M3) no fue registrado.
        """

    @abstractmethod
    def export_csv(self, report: PipelineReport, path: str) -> None:
        """
        Exporta las métricas del reporte a un archivo CSV.

        Args:
            report: PipelineReport construido con build_report()
            path  : ruta de destino del archivo CSV
        """

    # ── Métricas derivadas con implementación por defecto ──────────────────

    def overall_efficiency(self, report: PipelineReport) -> float:
        """
        Eficiencia end-to-end del pipeline:
            η = H(X) / L̄  ×  (1 − BER_after)
        Combina la eficiencia de compresión con la confiabilidad del canal.
        """
        cr = report.compression_result
        ber_after = (
            report.coding_stats.ber_after
            if report.coding_stats
            else report.transmission.ber
        )
        h = report.source_stats.entropy
        l_bar = cr.codebook.avg_length
        compression_eff = h / l_bar if l_bar > 0 else 0.0
        return compression_eff * (1 - ber_after)


# ── Interfaz de visualización ──────────────────────────────────────────────

class Visualizer(ABC):
    """
    Responsable de generar todas las representaciones visuales del pipeline.
    Puede implementarse con matplotlib, Streamlit, o cualquier otra librería.

    Flujo de uso:
        viz = ConcreteVisualizer()
        viz.plot_ber_curve(reports)         # curva BER vs p
        viz.plot_compression_comparison(reports)
        viz.plot_source_histogram(report)
        viz.plot_codebook_tree(codebook)
        viz.show()  / viz.save(path)
    """

    @abstractmethod
    def plot_ber_curve(
        self,
        reports: list[PipelineReport],
        param_key: str = 'p',
    ) -> Any:
        """
        Curva BER vs parámetro del canal (usualmente probabilidad de error p).
        Grafica BER antes y después de corrección si M4 está disponible.

        Args:
            reports  : lista de PipelineReport, uno por valor de p simulado
            param_key: clave del parámetro a usar como eje X (default: 'p')

        Returns:
            Objeto figura (matplotlib Figure, plotly Figure, etc.)
        """

    @abstractmethod
    def plot_compression_comparison(
        self,
        reports: list[PipelineReport],
    ) -> Any:
        """
        Gráfica comparativa de eficiencia y tasa de compresión entre
        múltiples codecs (Huffman, Tunstall k=2, Tunstall k=3, etc.).

        Args:
            reports: un PipelineReport por codec a comparar

        Returns:
            Objeto figura con las barras/curvas comparativas.
        """

    @abstractmethod
    def plot_source_histogram(self, report: PipelineReport) -> Any:
        """
        Histograma de frecuencias de símbolos de la fuente con la
        curva de distribución teórica superpuesta.

        Args:
            report: cualquier PipelineReport (usa report.source_stats)

        Returns:
            Objeto figura con el histograma.
        """

    @abstractmethod
    def plot_codebook_tree(self, report: PipelineReport) -> Any:
        """
        Visualiza el árbol de codificación (árbol de Huffman o árbol de
        expansión de Tunstall) del codec usado en el reporte.

        Args:
            report: PipelineReport con el codebook a visualizar

        Returns:
            Objeto figura con el árbol.
        """

    @abstractmethod
    def show(self) -> None:
        """Muestra todas las figuras generadas (bloquea hasta cerrar en matplotlib)."""

    @abstractmethod
    def save(self, path: str, fmt: str = 'png') -> None:
        """
        Guarda todas las figuras en archivos.

        Args:
            path: directorio de destino
            fmt : formato de imagen ('png', 'pdf', 'svg')
        """
