from __future__ import annotations

from datetime import datetime

from data_pipeline.core.pipeline import Extractor, FacilityStore
from data_pipeline.orchestration.airflow_adapter import AIRFLOW_AVAILABLE, create_daily_sync_dag


class PlaceholderExtractor(Extractor[dict]):
    async def extract(self) -> list[dict]:
        # Replace with a real provider extractor in production.
        return []


class PlaceholderStore(FacilityStore):
    async def upsert_many(self, records):
        # Replace with a real repository/store implementation in production.
        return len(records)


if AIRFLOW_AVAILABLE:
    dag = create_daily_sync_dag(
        dag_id="seoul_care_plus_daily_sync",
        extractor_factory=lambda: PlaceholderExtractor(),
        store_factory=lambda: PlaceholderStore(),
        schedule="@daily",
        start_date=datetime(2026, 1, 1),
    )
else:
    dag = None

