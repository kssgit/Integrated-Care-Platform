from fastapi.testclient import TestClient

from api.app import create_app
from api.cache import FacilityCache, InMemoryCacheStore
from api.dependencies import get_facility_cache


def test_internal_event_invalidate_facility_cache() -> None:
    app = create_app()
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    app.dependency_overrides[get_facility_cache] = lambda: cache
    client = TestClient(app)

    import asyncio

    asyncio.run(cache.set("facilities:page:1:20:*:20:*", {"success": True}))
    response = client.post("/v1/internal/events", json={"event_type": "etl_completed"})
    invalidated = response.json()["data"]["invalidated_keys"]
    cached = asyncio.run(cache.get("facilities:page:1:20:*:20:*"))

    assert response.status_code == 200
    assert invalidated >= 1
    assert cached is None


def test_internal_event_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_EVENT_TOKEN", "secret-token")
    client = TestClient(create_app())
    response = client.post("/v1/internal/events", json={"event_type": "etl_completed"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    monkeypatch.delenv("INTERNAL_EVENT_TOKEN")
