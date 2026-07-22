"""
M5 — PipelineMetrics

Implementación concreta de MetricsCollector.
Agrega resultados de M1–M4, calcula métricas derivadas y exporta CSV.
"""
from __future__ import annotations
import csv
import os
from dataclasses import dataclass, field
from typing import Any
#from . import PipelineReport


# ── Dataclasses (inlined para no depender de imports circulares) ───────────

@dataclass
class PipelineReport:
    source_stats:        Any
    compression_result:  Any
    codec_name:          str
    transmission:        Any
    channel_params:      dict
    decoded:             Any | None = None
    coding_stats:        Any | None = None
    extra:               dict = field(default_factory=dict)


class PipelineMetrics:
    """
    Colecta, consolida y exporta métricas de una ejecución del pipeline.

    Uso:
        m = PipelineMetrics()
        m.register_source(stats)
        m.register_compression(result, 'Tunstall k=3')
        m.register_transmission(trans)
        m.register_correction(decoded, coding_stats)   # opcional
        report = m.build_report()
        m.export_csv(report, 'out/metrics.csv')
    """

    def __init__(self) -> None:
        self._source      = None
        self._compression = None
        self._codec_name  = ""
        self._transmission= None
        self._decoded     = None
        self._coding_stats= None

    # ── Registro ───────────────────────────────────────────────────────────

    def register_source(self, stats) -> None:
        self._source = stats

    def register_compression(self, result, codec_name: str) -> None:
        self._compression = result
        self._codec_name  = codec_name

    def register_transmission(self, result) -> None:
        self._transmission = result

    def register_correction(self, decoded, stats) -> None:
        self._decoded      = decoded
        self._coding_stats = stats

    def reset(self) -> None:
        """Limpia el estado para reutilizar el colector en una nueva ejecución."""
        self.__init__()

    # ── Build ──────────────────────────────────────────────────────────────

    def build_report(self) -> PipelineReport:
        if self._source is None:
            raise RuntimeError("M1 no registrado. Llama register_source().")
        if self._compression is None:
            raise RuntimeError("M2 no registrado. Llama register_compression().")
        if self._transmission is None:
            raise RuntimeError("M3 no registrado. Llama register_transmission().")

        # Calcular eficiencia global
        h     = self._source.entropy
        cb    = self._compression.codebook
        l_bar = cb.avg_length
        ber   = (self._coding_stats.ber_after
                 if self._coding_stats else self._transmission.ber)
        if cb.code_length is not None:
            # Longitud fija (Tunstall): L̄ está en símbolos/frase, no en
            # bits/símbolo, así que la tasa real es k / L̄ (ver
            # TunstallCodec.compute_efficiency).
            rate     = cb.code_length / l_bar if l_bar > 0 else 0.0
            comp_eff = rate / h if h > 0 else 0.0
        else:
            comp_eff = h / l_bar if l_bar > 0 else 0.0
        overall   = comp_eff * (1 - ber)

        return PipelineReport(
            source_stats       = self._source,
            compression_result = self._compression,
            codec_name         = self._codec_name,
            transmission       = self._transmission,
            channel_params     = self._transmission.params,
            decoded            = self._decoded,
            coding_stats       = self._coding_stats,
            extra              = {
                'compression_efficiency': comp_eff,
                'overall_efficiency'    : overall,
                'ber_final'             : ber,
            },
        )

    # ── Export ─────────────────────────────────────────────────────────────

    def export_csv(self, report: PipelineReport, path: str) -> None:
        """Exporta las métricas principales del reporte a un CSV."""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        rows = self._report_to_rows(report)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Métrica', 'Valor', 'Unidad'])
            w.writerows(rows)

    def summary_dict(self, report: PipelineReport) -> dict:
        """Retorna todas las métricas como diccionario plano."""
        return {k: v for k, v, _ in self._report_to_rows(report)}

    # ── Utilidad privada ───────────────────────────────────────────────────

    def _report_to_rows(self, r: PipelineReport) -> list[tuple]:
        s   = r.source_stats
        cr  = r.compression_result
        cb  = cr.codebook
        tr  = r.transmission
        cs  = r.coding_stats
        ex  = r.extra

        rows = [
            # M1
            ('Codec',                  r.codec_name,                    ''),
            ('Fuente — tipo',          s.metadata.get('source_type',''),''),
            ('Fuente — símbolos',      len(s.symbols),                  'símbolos'),
            ('Alfabeto',               len(s.alphabet),                 'símbolos únicos'),
            ('Entropía H(X)',          round(s.entropy, 6),             'bits/símbolo'),
            # M2
            ('Longitud media L̄',      round(cb.avg_length, 6),         'bits/símbolo'),
            ('Tasa compresión',        round(cr.compression_ratio, 4),  'x'),
            ('Bits originales',        cr.original_bits,                'bits'),
            ('Bits comprimidos',       cr.compressed_bits,              'bits'),
            ('Eficiencia compresión',  round(ex.get('compression_efficiency', 0)*100, 2), '%'),
            # M3
            ('Canal — parámetros',     str(r.channel_params),           ''),
            ('Capacidad canal C',      round(tr.capacity, 6),           'bits/uso'),
            ('Bits erróneos',          tr.bit_errors,                   'bits'),
            ('BER (antes corrección)', round(tr.ber, 8),                ''),
        ]
        # M4 (opcional)
        if cs:
            rows += [
                ('BER (después corrección)', round(cs.ber_after, 8),        ''),
                ('Ganancia codificación',    round(cs.coding_gain_db, 4),   'dB'),
                ('Bloques totales',          cs.total_blocks,               ''),
                ('Bloques fallidos',         cs.failed_blocks,              ''),
            ]
        rows += [
            ('Eficiencia global η',    round(ex.get('overall_efficiency',0)*100, 2), '%'),
        ]
        return rows