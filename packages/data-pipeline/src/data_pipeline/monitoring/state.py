from __future__ import annotations

from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.core.prometheus_exporter import PipelinePrometheusExporter

pipeline_metrics = InMemoryPipelineMetricsCollector()
pipeline_exporter = PipelinePrometheusExporter()

