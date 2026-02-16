from datetime import datetime

import pytest

from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.core.pipeline import ETLPipeline, Extractor, FacilityStore


class MetricExtractor(Extractor[dict]):
    async def extract(self) -> list[dict]:
        return [
            {
                "source_id": "A1",
                "name": "Alpha",
                "address": "Seoul Jongno-gu",
                "district_code": "11110",
                "lat": 37.57,
                "lng": 126.98,
                "source_updated_at": datetime(2026, 1, 2),
            }
        ]


class MetricStore(FacilityStore):
    async def upsert_many(self, records):
        return len(records)


@pytest.mark.asyncio
async def test_pipeline_collects_stage_metrics() -> None:
    metrics = InMemoryPipelineMetricsCollector()
    pipeline = ETLPipeline(extractor=MetricExtractor(), store=MetricStore(), metrics=metrics)

    saved_count = await pipeline.run()

    assert saved_count == 1
    assert metrics.processed_records == 1
    assert metrics.pipeline_run_total[("unknown", "success")] == 1
    assert metrics.pipeline_records_total[("unknown", "accepted")] == 1
    stages = {item.stage for item in metrics.stage_durations}
    assert "extract" in stages
    assert "validate" in stages
    assert "normalize" in stages
    assert "quality" in stages
    assert "deduplicate" in stages
    assert "store" in stages
    assert "etl_total" in stages
