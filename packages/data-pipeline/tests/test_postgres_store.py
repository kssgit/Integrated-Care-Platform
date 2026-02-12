from __future__ import annotations

from datetime import datetime

import pytest

from data_pipeline.core.models import FacilityRecord
from data_pipeline.jobs.postgres_store import PostgresFacilityStore, UPSERT_SQL


class FakePool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[tuple]]] = []

    async def executemany(self, sql: str, values: list[tuple]) -> None:
        self.calls.append((sql, values))


@pytest.mark.asyncio
async def test_postgres_store_executes_upsert_many() -> None:
    pool = FakePool()

    async def pool_factory(_: str):
        return pool

    store = PostgresFacilityStore("postgresql://example", pool_factory=pool_factory)
    record = FacilityRecord(
        source_id="A1",
        name="Center",
        address="Seoul",
        district_code="11110",
        lat=37.5,
        lng=126.9,
        source_updated_at=datetime(2026, 1, 1),
    )
    saved = await store.upsert_many([record])

    assert saved == 1
    assert len(pool.calls) == 1
    assert UPSERT_SQL.strip() in pool.calls[0][0]
    assert pool.calls[0][1][0][0] == "A1"


@pytest.mark.asyncio
async def test_postgres_store_splits_batches() -> None:
    pool = FakePool()

    async def pool_factory(_: str):
        return pool

    store = PostgresFacilityStore("postgresql://example", batch_size=2, pool_factory=pool_factory)
    records = [
        FacilityRecord(
            source_id=f"A{idx}",
            name="Center",
            address="Seoul",
            district_code="11110",
            lat=37.5,
            lng=126.9,
            source_updated_at=datetime(2026, 1, 1),
        )
        for idx in range(5)
    ]

    saved = await store.upsert_many(records)

    assert saved == 5
    assert len(pool.calls) == 3
    assert len(pool.calls[0][1]) == 2
    assert len(pool.calls[1][1]) == 2
    assert len(pool.calls[2][1]) == 1
