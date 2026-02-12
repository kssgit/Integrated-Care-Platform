import pytest

from api.cache import FacilityCache, InMemoryCacheStore
from api.event_consumer import ApiEventConsumer


@pytest.mark.asyncio
async def test_event_consumer_invalidates_cache_on_etl_completed() -> None:
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    consumer = ApiEventConsumer(cache=cache)

    await cache.set("facilities:page:1:20:*:20:*", {"success": True})
    removed = await consumer.handle_payload({"event_type": "etl_completed", "saved_count": 10})
    cached = await cache.get("facilities:page:1:20:*:20:*")

    assert removed == 1
    assert cached is None


@pytest.mark.asyncio
async def test_event_consumer_ignores_non_etl_event() -> None:
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    consumer = ApiEventConsumer(cache=cache)

    await cache.set("facilities:page:1:20:*:20:*", {"success": True})
    removed = await consumer.handle_payload({"event_type": "other_event"})
    cached = await cache.get("facilities:page:1:20:*:20:*")

    assert removed == 0
    assert cached is not None

