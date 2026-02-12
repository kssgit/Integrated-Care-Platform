import pytest

from api.event_dedup import InMemoryProcessedEventStore


@pytest.mark.asyncio
async def test_inmemory_processed_event_store_marks_once() -> None:
    store = InMemoryProcessedEventStore()
    first = await store.mark_once("trace-1", ttl_seconds=60)
    second = await store.mark_once("trace-1", ttl_seconds=60)

    assert first is True
    assert second is False

