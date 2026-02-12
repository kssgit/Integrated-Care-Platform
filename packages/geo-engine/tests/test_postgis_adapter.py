from __future__ import annotations

import pytest

from geo_engine.models import GeoPoint
from geo_engine.postgis_adapter import DISTANCE_SQL, NEAREST_FACILITIES_SQL, PostGISAdapter


class FakePool:
    def __init__(self) -> None:
        self.fetchval_calls: list[tuple[str, tuple]] = []
        self.fetch_calls: list[tuple[str, tuple]] = []

    async def fetchval(self, sql: str, *args):
        self.fetchval_calls.append((sql, args))
        return 1234.567

    async def fetch(self, sql: str, *args):
        self.fetch_calls.append((sql, args))
        return [
            {
                "source_id": "A1",
                "name": "Center A",
                "district_code": "11110",
                "lat": 37.57,
                "lng": 126.98,
                "distance_meters": 777.77,
            }
        ]


@pytest.mark.asyncio
async def test_postgis_adapter_distance_meters() -> None:
    pool = FakePool()

    async def pool_factory(_: str):
        return pool

    adapter = PostGISAdapter("postgresql://example", pool_factory=pool_factory)
    distance = await adapter.distance_meters(
        GeoPoint(lat=37.5665, lng=126.9780),
        GeoPoint(lat=37.5700, lng=126.9900),
    )

    assert distance == 1234.57
    assert DISTANCE_SQL.strip() in pool.fetchval_calls[0][0]


@pytest.mark.asyncio
async def test_postgis_adapter_nearest_facilities() -> None:
    pool = FakePool()

    async def pool_factory(_: str):
        return pool

    adapter = PostGISAdapter("postgresql://example", pool_factory=pool_factory)
    items = await adapter.nearest_facilities(
        center=GeoPoint(lat=37.5665, lng=126.9780),
        limit=3,
        district_code="11110",
    )

    assert len(items) == 1
    assert items[0]["source_id"] == "A1"
    assert NEAREST_FACILITIES_SQL.strip() in pool.fetch_calls[0][0]


@pytest.mark.asyncio
async def test_postgis_adapter_nearest_facilities_rejects_invalid_limit() -> None:
    pool = FakePool()

    async def pool_factory(_: str):
        return pool

    adapter = PostGISAdapter("postgresql://example", pool_factory=pool_factory)
    with pytest.raises(ValueError):
        await adapter.nearest_facilities(center=GeoPoint(lat=37.5, lng=126.9), limit=0)
