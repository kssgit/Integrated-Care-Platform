from __future__ import annotations

from prometheus_client import CollectorRegistry, Gauge, generate_latest

from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector


class PipelinePrometheusExporter:
    def __init__(self) -> None:
        self._registry = CollectorRegistry()
        self._stage_duration = Gauge(
            "etl_stage_duration_ms",
            "ETL stage duration in milliseconds",
            labelnames=("stage",),
            registry=self._registry,
        )
        self._external_errors = Gauge(
            "etl_external_api_errors_total",
            "ETL external API error count",
            registry=self._registry,
        )
        self._processed_records = Gauge(
            "etl_processed_records_total",
            "ETL processed record count",
            registry=self._registry,
        )

    def render(self, metrics: InMemoryPipelineMetricsCollector) -> str:
        latest_by_stage: dict[str, float] = {}
        for item in metrics.stage_durations:
            latest_by_stage[item.stage] = item.duration_ms
        for stage, duration in latest_by_stage.items():
            self._stage_duration.labels(stage=stage).set(duration)
        self._external_errors.set(metrics.external_api_error_count)
        self._processed_records.set(metrics.processed_records)
        return generate_latest(self._registry).decode("utf-8")

