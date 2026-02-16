from fastapi.testclient import TestClient

from api.app import create_app
from api.cache import FacilityCache, InMemoryCacheStore
from api.circuit_breaker import CircuitBreaker
from api.dependencies import get_circuit_breaker, get_facility_cache, get_facility_service, get_rate_limiter
from api.rate_limit import InMemoryRateLimitStore, SlidingWindowRateLimiter
from api.schemas.facility import FacilityItem


class FailingService:
    async def list_facilities(self, _query):
        raise RuntimeError("provider failed")


class CountingService:
    def __init__(self) -> None:
        self.called = 0

    async def list_facilities(self, query):
        self.called += 1
        start = (query.page - 1) * query.page_size + 1
        item = FacilityItem(id=f"fac-{start}", name="Cached Center", district_code="11110")
        return [item], 1


def test_health_endpoint_response_shape() -> None:
    client = TestClient(create_app())
    response = client.get("/healthz")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_ready_endpoint_response_shape() -> None:
    client = TestClient(create_app())
    response = client.get("/readyz")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["status"] == "ready"


def test_dev_api_test_page_exists() -> None:
    client = TestClient(create_app())
    response = client.get("/dev/api-test")
    assert response.status_code == 200
    assert "Integrated Care API Quick Test" in response.text


def test_facilities_endpoint_pagination_response_shape() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/v1/facilities?page=1&page_size=2")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert len(body["data"]) == 2
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["next_cursor"] is None


def test_facilities_rate_limit_error_format() -> None:
    app = create_app()
    limiter = SlidingWindowRateLimiter(InMemoryRateLimitStore(), limit_per_minute=1, window_seconds=60)
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    client = TestClient(app)

    first = client.get("/v1/facilities", headers={"x-client-id": "client-1"})
    second = client.get("/v1/facilities", headers={"x-client-id": "client-1"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_facilities_upstream_failure_is_isolated() -> None:
    app = create_app()
    app.dependency_overrides[get_facility_service] = lambda: FailingService()
    app.dependency_overrides[get_facility_cache] = lambda: FacilityCache(
        store=InMemoryCacheStore(),
        ttl_seconds=60,
    )
    app.dependency_overrides[get_circuit_breaker] = lambda: CircuitBreaker(
        failure_threshold=3,
        recovery_timeout_seconds=30,
    )
    client = TestClient(app)

    response = client.get("/v1/facilities")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_FAILURE"


def test_facilities_validation_error_shape() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/facilities?page=0&page_size=20")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_facilities_uses_cache_for_same_query() -> None:
    app = create_app()
    service = CountingService()
    cache = FacilityCache(
        store=InMemoryCacheStore(),
        ttl_seconds=60,
    )
    app.dependency_overrides[get_facility_service] = lambda: service
    app.dependency_overrides[get_facility_cache] = lambda: cache
    client = TestClient(app)

    first = client.get("/v1/facilities?page=1&page_size=1&district_code=11110")
    second = client.get("/v1/facilities?page=1&page_size=1&district_code=11110")

    assert first.status_code == 200
    assert second.status_code == 200
    assert service.called == 1


def test_facilities_cursor_mode_response_shape() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/facilities?cursor=0&limit=1")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["meta"]["next_cursor"] == "1"
