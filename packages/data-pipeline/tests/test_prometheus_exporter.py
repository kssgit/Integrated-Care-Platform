from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.core.prometheus_exporter import PipelinePrometheusExporter


def test_pipeline_prometheus_exporter_renders_metrics() -> None:
    metrics = InMemoryPipelineMetricsCollector()
    metrics.observe_stage_duration("extract", 12.5)
    metrics.observe_stage_duration("store", 4.1)
    metrics.increment_external_api_error()
    metrics.add_processed_records(8)

    output = PipelinePrometheusExporter().render(metrics)

    assert "etl_stage_duration_ms" in output
    assert 'stage="extract"' in output
    assert "etl_external_api_errors_total" in output
    assert "etl_processed_records_total" in output

