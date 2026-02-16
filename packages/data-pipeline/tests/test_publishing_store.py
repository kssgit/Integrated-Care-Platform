from __future__ import annotations

from datetime import datetime

import pytest

from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.pipeline import FacilityStore
from data_pipeline.jobs.publishing_store import PublishingFacilityStore
from data_pipeline.messaging.broker import InMemoryMessageBroker
from data_pipeline.messaging.topics import ETL_NORMALIZED_TOPIC


class StubStore(FacilityStore):
    async def upsert_many(self, records: list[FacilityRecord]) -> int:
        return len(records)


@pytest.mark.asyncio
async def test_publishing_store_emits_normalized_events() -> None:
    broker = InMemoryMessageBroker()
    store = PublishingFacilityStore(
        delegate=StubStore(),
        broker=broker,
        provider="seoul_open_data",
    )
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
    assert len(broker.published[ETL_NORMALIZED_TOPIC]) == 1
    assert broker.published[ETL_NORMALIZED_TOPIC][0].payload["source_id"] == "A1"


class FailingBroker(InMemoryMessageBroker):
    async def publish(self, topic, message):  # noqa: ANN001
        del topic, message
        raise RuntimeError("publish failure")


@pytest.mark.asyncio
async def test_publishing_store_raises_when_publish_fails_after_save() -> None:
    store = PublishingFacilityStore(
        delegate=StubStore(),
        broker=FailingBroker(),
        provider="seoul_open_data",
    )
    record = FacilityRecord(
        source_id="A1",
        name="Center",
        address="Seoul",
        district_code="11110",
        lat=37.5,
        lng=126.9,
        source_updated_at=datetime(2026, 1, 1),
    )

    with pytest.raises(RuntimeError, match="publish failed after successful save"):
        await store.upsert_many([record])
