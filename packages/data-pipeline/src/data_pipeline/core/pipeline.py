from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
import logging
from typing import Generic, TypeVar

from data_pipeline.core.exceptions import ValidationError
from data_pipeline.core.models import FacilityRecord

T = TypeVar("T")
logger = logging.getLogger(__name__)


class Extractor(ABC, Generic[T]):
    @abstractmethod
    async def extract(self) -> list[T]:
        raise NotImplementedError


class FacilityStore(ABC):
    @abstractmethod
    async def upsert_many(self, records: list[FacilityRecord]) -> int:
        raise NotImplementedError


class ETLPipeline:
    def __init__(self, extractor: Extractor[dict], store: FacilityStore) -> None:
        self._extractor = extractor
        self._store = store

    async def run(self) -> int:
        logger.info("etl_run_started", extra={"component": "data_pipeline"})
        extracted = await self._extractor.extract()
        validated = [self._validate(item) for item in extracted]
        normalized = [self._normalize(item) for item in validated]
        deduplicated = list(self._deduplicate(normalized))
        saved_count = await self._store.upsert_many(deduplicated)
        logger.info(
            "etl_run_completed",
            extra={"component": "data_pipeline", "saved_count": saved_count},
        )
        return saved_count

    def _validate(self, payload: dict) -> dict:
        required = [
            "source_id",
            "name",
            "address",
            "district_code",
            "lat",
            "lng",
            "source_updated_at",
        ]
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValidationError(f"missing required fields: {', '.join(missing)}")
        return payload

    def _normalize(self, payload: dict) -> FacilityRecord:
        address = " ".join(str(payload["address"]).split())
        return FacilityRecord(
            source_id=str(payload["source_id"]),
            name=str(payload["name"]).strip(),
            address=address,
            district_code=str(payload["district_code"]).strip(),
            lat=float(payload["lat"]),
            lng=float(payload["lng"]),
            source_updated_at=payload["source_updated_at"],
        )

    def _deduplicate(
        self,
        records: Iterable[FacilityRecord],
    ) -> Iterable[FacilityRecord]:
        latest_by_source: dict[str, FacilityRecord] = {}
        for record in records:
            existing = latest_by_source.get(record.source_id)
            if existing is None or record.source_updated_at > existing.source_updated_at:
                latest_by_source[record.source_id] = record
        return latest_by_source.values()
