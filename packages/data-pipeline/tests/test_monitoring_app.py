from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from data_pipeline.jobs.daily_sync import run_daily_sync
from data_pipeline.monitoring.app import create_monitoring_app
from data_pipeline.monitoring.state import pipeline_metrics
from data_pipeline.core.pipeline import Extractor, FacilityStore


class StubExtractor(Extractor[dict]):
    async def extract(self) -> list[dict]:
        return [
            {
                "source_id": "S1",
                "name": "Center",
                "address": "Seoul Mapo-gu",
                "district_code": "11440",
                "lat": 37.56,
                "lng": 126.9,
                "source_updated_at": datetime(2026, 1, 1),
            }
        ]


class StubStore(FacilityStore):
    async def upsert_many(self, records):
        return len(records)


def test_pipeline_metrics_endpoint_exposes_pipeline_metrics() -> None:
    pipeline_metrics.stage_durations.clear()
    pipeline_metrics.external_api_error_count = 0
    pipeline_metrics.processed_records = 0

    import asyncio

    asyncio.run(run_daily_sync(StubExtractor(), StubStore()))
    client = TestClient(create_monitoring_app())
    response = client.get("/metrics")
    body = response.text

    assert response.status_code == 200
    assert "etl_stage_duration_ms" in body
    assert "etl_processed_records_total" in body

