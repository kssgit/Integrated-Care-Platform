import pytest

from api.cache import FacilityCache, InMemoryCacheStore


@pytest.mark.asyncio
async def test_inmemory_cache_store_get_set() -> None:
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    key = "facilities:1:20:*"
    payload = {"success": True, "data": [{"id": "a"}], "meta": {"page": 1}}

    await cache.set(key, payload)
    cached = await cache.get(key)

    assert cached == payload

