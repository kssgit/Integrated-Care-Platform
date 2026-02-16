from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.core.prometheus_exporter import PipelinePrometheusExporter


def test_pipeline_prometheus_exporter_renders_metrics() -> None:
    metrics = InMemoryPipelineMetricsCollector()
    metrics.observe_stage_duration("extract", 12.5)
    metrics.observe_stage_duration("store", 4.1)
    metrics.increment_external_api_error()
    metrics.add_processed_records(8)
    metrics.increment_run(status="success", provider="seoul_open_data")
    metrics.add_records(result="rejected", count=2, provider="seoul_open_data")
    metrics.set_reject_ratio(0.2, provider="seoul_open_data")
    metrics.observe_pipeline_duration(1.5, provider="seoul_open_data")
    metrics.increment_provider_http_error(code=500, provider="seoul_open_data")

    output = PipelinePrometheusExporter().render(metrics)

    assert "etl_stage_duration_ms" in output
    assert 'stage="extract"' in output
    assert "etl_external_api_errors_total" in output
    assert "etl_processed_records_total" in output
    assert "pipeline_run_total" in output
    assert "pipeline_records_total" in output
    assert "pipeline_reject_ratio" in output
    assert "pipeline_duration_seconds" in output
    assert "pipeline_provider_http_errors_total" in output
