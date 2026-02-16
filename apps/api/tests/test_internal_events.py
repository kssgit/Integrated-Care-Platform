from fastapi.testclient import TestClient

from api.app import create_app
from api.cache import FacilityCache, InMemoryCacheStore
from api.dependencies import get_facility_cache
from shared.security import build_event_signature


def test_internal_event_invalidate_facility_cache(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_EVENT_TOKEN", "secret-token")
    app = create_app()
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    app.dependency_overrides[get_facility_cache] = lambda: cache
    client = TestClient(app)

    import asyncio

    asyncio.run(cache.set("facilities:page:1:20:*:20:*", {"success": True}))
    response = client.post(
        "/v1/internal/events",
        json={"event_type": "etl_completed"},
        headers={"x-internal-token": "secret-token"},
    )
    invalidated = response.json()["data"]["invalidated_keys"]
    cached = asyncio.run(cache.get("facilities:page:1:20:*:20:*"))

    assert response.status_code == 200
    assert invalidated >= 1
    assert cached is None
    monkeypatch.delenv("INTERNAL_EVENT_TOKEN")


def test_internal_event_requires_token_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_EVENT_TOKEN", "secret-token")
    client = TestClient(create_app())
    response = client.post("/v1/internal/events", json={"event_type": "etl_completed"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    monkeypatch.delenv("INTERNAL_EVENT_TOKEN")


def test_internal_event_hmac_signature(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_EVENT_HMAC_SECRET", "hmac-secret")
    client = TestClient(create_app())
    payload = '{"event_type":"etl_completed"}'
    import time

    timestamp = str(int(time.time()))
    signature = build_event_signature("hmac-secret", timestamp, payload)
    ok = client.post(
        "/v1/internal/events",
        data=payload,
        headers={
            "x-event-signature": signature,
            "x-event-timestamp": timestamp,
            "content-type": "application/json",
        },
    )
    assert ok.status_code == 200

    stale_timestamp = "1700000000"
    stale_signature = build_event_signature("hmac-secret", stale_timestamp, payload)
    response = client.post(
        "/v1/internal/events",
        data=payload,
        headers={
            "x-event-signature": stale_signature,
            "x-event-timestamp": stale_timestamp,
            "content-type": "application/json",
        },
    )
    # old timestamp should fail due replay window
    assert response.status_code == 401
    monkeypatch.delenv("INTERNAL_EVENT_HMAC_SECRET")


def test_internal_event_fails_when_auth_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("INTERNAL_EVENT_HMAC_SECRET", raising=False)
    monkeypatch.delenv("INTERNAL_EVENT_TOKEN", raising=False)
    client = TestClient(create_app())
    response = client.post("/v1/internal/events", json={"event_type": "etl_completed"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INTERNAL_EVENT_AUTH_NOT_CONFIGURED"
