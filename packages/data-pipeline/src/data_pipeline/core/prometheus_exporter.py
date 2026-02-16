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
        self._pipeline_run_total = Gauge(
            "pipeline_run_total",
            "Pipeline runs grouped by provider and status",
            labelnames=("provider", "status"),
            registry=self._registry,
        )
        self._pipeline_records_total = Gauge(
            "pipeline_records_total",
            "Pipeline record counts grouped by provider and result",
            labelnames=("provider", "result"),
            registry=self._registry,
        )
        self._pipeline_reject_ratio = Gauge(
            "pipeline_reject_ratio",
            "Reject ratio by provider",
            labelnames=("provider",),
            registry=self._registry,
        )
        self._pipeline_duration_seconds = Gauge(
            "pipeline_duration_seconds",
            "Pipeline run duration by provider",
            labelnames=("provider",),
            registry=self._registry,
        )
        self._pipeline_http_errors_total = Gauge(
            "pipeline_provider_http_errors_total",
            "Provider HTTP errors grouped by provider and code",
            labelnames=("provider", "code"),
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
        for (provider, status), count in metrics.pipeline_run_total.items():
            self._pipeline_run_total.labels(provider=provider, status=status).set(count)
        for (provider, result), count in metrics.pipeline_records_total.items():
            self._pipeline_records_total.labels(provider=provider, result=result).set(count)
        for provider, ratio in metrics.pipeline_reject_ratio.items():
            self._pipeline_reject_ratio.labels(provider=provider).set(ratio)
        for provider, duration in metrics.pipeline_duration_seconds.items():
            self._pipeline_duration_seconds.labels(provider=provider).set(duration)
        for (provider, code), count in metrics.pipeline_provider_http_errors_total.items():
            self._pipeline_http_errors_total.labels(provider=provider, code=code).set(count)
        return generate_latest(self._registry).decode("utf-8")
