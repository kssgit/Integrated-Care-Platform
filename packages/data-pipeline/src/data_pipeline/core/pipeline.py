from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
import logging
from time import perf_counter
from typing import Awaitable, Callable, Generic, TypeVar

from data_pipeline.core.exceptions import ValidationError
from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.core.models import FacilityRecord

T = TypeVar("T")
R = TypeVar("R")
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
    def __init__(
        self,
        extractor: Extractor[dict],
        store: FacilityStore,
        metrics: InMemoryPipelineMetricsCollector | None = None,
    ) -> None:
        self._extractor = extractor
        self._store = store
        self._metrics = metrics

    async def run(self) -> int:
        logger.info("etl_run_started", extra={"component": "data_pipeline"})
        total_started = perf_counter()
        extracted = await self._time_async("extract", self._extractor.extract)
        validated = [self._validate(item) for item in extracted]
        normalized = [self._normalize(item) for item in validated]
        deduplicated = self._time_sync("deduplicate", lambda: list(self._deduplicate(normalized)))
        saved_count = await self._time_async("store", lambda: self._store.upsert_many(deduplicated))
        self._observe("etl_total", (perf_counter() - total_started) * 1000.0)
        if self._metrics:
            self._metrics.add_processed_records(saved_count)
        logger.info(
            "etl_run_completed",
            extra={"component": "data_pipeline", "saved_count": saved_count},
        )
        return saved_count

    def _validate(self, payload: dict) -> dict:
        started = perf_counter()
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
        self._observe("validate", (perf_counter() - started) * 1000.0)
        return payload

    def _normalize(self, payload: dict) -> FacilityRecord:
        started = perf_counter()
        address = " ".join(str(payload["address"]).split())
        normalized = FacilityRecord(
            source_id=str(payload["source_id"]),
            name=str(payload["name"]).strip(),
            address=address,
            district_code=str(payload["district_code"]).strip(),
            lat=float(payload["lat"]),
            lng=float(payload["lng"]),
            source_updated_at=payload["source_updated_at"],
        )
        self._observe("normalize", (perf_counter() - started) * 1000.0)
        return normalized

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

    async def _time_async(self, stage: str, action: Callable[[], Awaitable[R]]) -> R:
        started = perf_counter()
        result = await action()
        self._observe(stage, (perf_counter() - started) * 1000.0)
        return result

    def _time_sync(self, stage: str, action: Callable[[], R]) -> R:
        started = perf_counter()
        result = action()
        self._observe(stage, (perf_counter() - started) * 1000.0)
        return result

    def _observe(self, stage: str, duration_ms: float) -> None:
        if self._metrics:
            self._metrics.observe_stage_duration(stage, duration_ms)
