from __future__ import annotations

from collections import OrderedDict
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
        batch_size: int = 1000,
        pool_factory: Callable[[str], Awaitable[Any]] | None = None,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        self._dsn = dsn
        self._batch_size = batch_size
        self._pool = None
        self._pool_factory = pool_factory

    async def upsert_many(self, records: list[FacilityRecord]) -> int:
        if not records:
            return 0
        deduplicated_records = self._deduplicate_for_idempotency(records)
        pool = await self._get_pool()
        for start in range(0, len(deduplicated_records), self._batch_size):
            batch = deduplicated_records[start : start + self._batch_size]
            values = [self._to_row(record) for record in batch]
            try:
                await pool.executemany(UPSERT_SQL, values)
            except Exception as exc:
                if self._is_non_retryable_error(exc):
                    raise RuntimeError("postgres upsert failed with non-retryable constraint error") from exc
                raise RuntimeError("postgres upsert failed due to transient error") from exc
        return len(deduplicated_records)

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

    def _deduplicate_for_idempotency(self, records: list[FacilityRecord]) -> list[FacilityRecord]:
        deduped: "OrderedDict[tuple[str, str], FacilityRecord]" = OrderedDict()
        for record in records:
            key = (record.source_id, record.source_updated_at.isoformat())
            deduped[key] = record
        return list(deduped.values())

    def _is_non_retryable_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "duplicate key" in message or "violates" in message or "constraint" in message
