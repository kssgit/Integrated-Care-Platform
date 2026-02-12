from datetime import datetime

import pytest

from data_pipeline.core.exceptions import ValidationError
from data_pipeline.core.pipeline import ETLPipeline, Extractor, FacilityStore


class StubExtractor(Extractor[dict]):
    async def extract(self) -> list[dict]:
        return [
            {
                "source_id": "A1",
                "name": " Alpha Center ",
                "address": "Seoul   Jongno-gu",
                "district_code": "11110",
                "lat": 37.57,
                "lng": 126.98,
                "source_updated_at": datetime(2026, 1, 1),
            },
            {
                "source_id": "A1",
                "name": "Alpha Center",
                "address": "Seoul Jongno-gu",
                "district_code": "11110",
                "lat": 37.57,
                "lng": 126.98,
                "source_updated_at": datetime(2026, 1, 2),
            },
        ]


class StubStore(FacilityStore):
    def __init__(self) -> None:
        self.saved = []

    async def upsert_many(self, records):
        self.saved = records
        return len(records)


class InvalidExtractor(Extractor[dict]):
    async def extract(self) -> list[dict]:
        return [{"source_id": "A1"}]


@pytest.mark.asyncio
async def test_pipeline_deduplicates_by_latest_source_updated_at() -> None:
    store = StubStore()
    pipeline = ETLPipeline(extractor=StubExtractor(), store=store)

    saved_count = await pipeline.run()

    assert saved_count == 1
    assert len(store.saved) == 1
    assert store.saved[0].source_id == "A1"
    assert store.saved[0].source_updated_at == datetime(2026, 1, 2)


@pytest.mark.asyncio
async def test_pipeline_raises_validation_error_on_invalid_payload() -> None:
    pipeline = ETLPipeline(extractor=InvalidExtractor(), store=StubStore())
    with pytest.raises(ValidationError):
        await pipeline.run()
