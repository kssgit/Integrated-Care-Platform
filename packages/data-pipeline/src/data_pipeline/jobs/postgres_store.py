from __future__ import annotations

from typing import Any, Awaitable, Callable

from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.pipeline import FacilityStore

UPSERT_SQL = """
INSERT INTO facility (
    source_id, name, address, district_code, lat, lng, source_updated_at
) VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (source_id) DO UPDATE
SET
    name = EXCLUDED.name,
    address = EXCLUDED.address,
    district_code = EXCLUDED.district_code,
    lat = EXCLUDED.lat,
    lng = EXCLUDED.lng,
    source_updated_at = EXCLUDED.source_updated_at
WHERE EXCLUDED.source_updated_at > facility.source_updated_at
"""


class PostgresFacilityStore(FacilityStore):
    def __init__(
        self,
        dsn: str,
        pool_factory: Callable[[str], Awaitable[Any]] | None = None,
    ) -> None:
        self._dsn = dsn
        self._pool = None
        self._pool_factory = pool_factory

    async def upsert_many(self, records: list[FacilityRecord]) -> int:
        if not records:
            return 0
        pool = await self._get_pool()
        values = [self._to_row(record) for record in records]
        await pool.executemany(UPSERT_SQL, values)
        return len(records)

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
            raise RuntimeError("asyncpg is required for postgres store") from exc
        return await asyncpg.create_pool(dsn=self._dsn, min_size=1, max_size=5)

    def _to_row(self, record: FacilityRecord) -> tuple:
        return (
            record.source_id,
            record.name,
            record.address,
            record.district_code,
            record.lat,
            record.lng,
            record.source_updated_at,
        )
