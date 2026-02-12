from __future__ import annotations

from datetime import datetime

import pytest

from data_pipeline.core.pipeline import Extractor, FacilityStore
from data_pipeline.orchestration.airflow_adapter import (
    AIRFLOW_AVAILABLE,
    build_daily_sync_callable,
    create_daily_sync_dag,
)


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


def test_build_daily_sync_callable_runs_pipeline() -> None:
    runner = build_daily_sync_callable(lambda: StubExtractor(), lambda: StubStore())
    saved_count = runner()
    assert saved_count == 1


def test_create_daily_sync_dag_requires_airflow() -> None:
    if AIRFLOW_AVAILABLE:
        dag = create_daily_sync_dag(
            "daily_sync_test",
            extractor_factory=lambda: StubExtractor(),
            store_factory=lambda: StubStore(),
        )
        assert dag is not None
        return

    with pytest.raises(RuntimeError):
        create_daily_sync_dag(
            "daily_sync_test",
            extractor_factory=lambda: StubExtractor(),
            store_factory=lambda: StubStore(),
        )

