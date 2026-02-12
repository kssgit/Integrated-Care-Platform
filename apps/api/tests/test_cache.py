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


@pytest.mark.asyncio
async def test_facility_cache_invalidate_facilities_prefix() -> None:
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    await cache.set("facilities:page:1:20:*:20:*", {"success": True})
    await cache.set("other:key", {"success": True})

    removed = await cache.invalidate_facilities()
    remaining = await cache.get("other:key")
    deleted = await cache.get("facilities:page:1:20:*:20:*")

    assert removed == 1
    assert remaining is not None
    assert deleted is None
