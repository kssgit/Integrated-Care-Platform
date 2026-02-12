import pytest

from api.cache import FacilityCache, InMemoryCacheStore
from api.event_consumer import ApiEventConsumer, EventConsumerConfig


@pytest.mark.asyncio
async def test_event_consumer_invalidates_cache_on_etl_completed() -> None:
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    consumer = ApiEventConsumer(cache=cache, config=EventConsumerConfig(max_retries=3))

    await cache.set("facilities:page:1:20:*:20:*", {"success": True})
    removed = await consumer.handle_payload({"event_type": "etl_completed", "saved_count": 10})
    cached = await cache.get("facilities:page:1:20:*:20:*")

    assert removed == 1
    assert cached is None


@pytest.mark.asyncio
async def test_event_consumer_ignores_non_etl_event() -> None:
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    consumer = ApiEventConsumer(cache=cache, config=EventConsumerConfig(max_retries=3))

    await cache.set("facilities:page:1:20:*:20:*", {"success": True})
    removed = await consumer.handle_payload({"event_type": "other_event"})
    cached = await cache.get("facilities:page:1:20:*:20:*")

    assert removed == 0
    assert cached is not None


@pytest.mark.asyncio
async def test_event_consumer_process_with_retry_sends_dlq() -> None:
    delays: list[float] = []
    dlq: list[tuple[bytes, str]] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    consumer = ApiEventConsumer(
        cache=FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60),
        config=EventConsumerConfig(max_retries=3, base_delay_seconds=0.1),
        sleep_fn=fake_sleep,
    )

    async def publish_dlq(value: bytes, error: str) -> None:
        dlq.append((value, error))

    await consumer._process_with_retry(b"not-json", publish_dlq)

    assert delays == [0.1, 0.2]
    assert len(dlq) == 1
    assert dlq[0][0] == b"not-json"
