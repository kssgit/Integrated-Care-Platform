from __future__ import annotations

from typing import Any, Awaitable, Callable

from geo_engine.models import GeoPoint

DISTANCE_SQL = """
SELECT ST_DistanceSphere(
    ST_MakePoint($1, $2),
    ST_MakePoint($3, $4)
)
"""

NEAREST_FACILITIES_SQL = """
SELECT
    source_id,
    name,
    district_code,
    lat,
    lng,
    ST_DistanceSphere(ST_MakePoint(lng, lat), ST_MakePoint($1, $2)) AS distance_meters
FROM facility
WHERE ($4::text IS NULL OR district_code = $4)
ORDER BY ST_MakePoint(lng, lat) <-> ST_MakePoint($1, $2)
LIMIT $3
"""


class PostGISAdapter:
    def __init__(
        self,
        dsn: str,
        pool_factory: Callable[[str], Awaitable[Any]] | None = None,
    ) -> None:
        self._dsn = dsn
        self._pool = None
        self._pool_factory = pool_factory

    async def distance_meters(self, start: GeoPoint, end: GeoPoint) -> float:
        pool = await self._get_pool()
        result = await pool.fetchval(DISTANCE_SQL, start.lng, start.lat, end.lng, end.lat)
        return round(float(result), 2)

    async def nearest_facilities(
        self,
        center: GeoPoint,
        limit: int = 5,
        district_code: str | None = None,
    ) -> list[dict]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        pool = await self._get_pool()
        rows = await pool.fetch(NEAREST_FACILITIES_SQL, center.lng, center.lat, limit, district_code)
        return [self._to_item(row) for row in rows]

    async def _get_pool(self) -> Any:
        if self._pool is not None:
            return self._pool
        self._pool = await self._create_pool()
        return self._pool

    async def _create_pool(self) -> Any:
        if self._pool_factory:
            return await self._pool_factory(self._dsn)
        try:
            import asyncpg
        except ImportError as exc:
            raise RuntimeError("asyncpg is required for postgis adapter") from exc
        return await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=5)

    def _to_item(self, row: Any) -> dict:
        return {
            "source_id": str(row["source_id"]),
            "name": str(row["name"]),
            "district_code": str(row["district_code"]),
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "distance_meters": round(float(row["distance_meters"]), 2),
        }
