from fastapi.testclient import TestClient

from api.app import create_app
from api.cache import FacilityCache, InMemoryCacheStore
from api.dependencies import get_facility_cache, get_geo_service
from api.schemas.geo import GeoDistanceResult, GeoNearestFacilitiesResult, GeoNearestFacilityItem


class CountingGeoService:
    def __init__(self) -> None:
        self.distance_calls = 0

    async def distance_meters(
        self,
        _origin_lat: float,
        _origin_lng: float,
        _target_lat: float,
        _target_lng: float,
    ) -> GeoDistanceResult:
        self.distance_calls += 1
        return GeoDistanceResult(distance_meters=123.45)

    async def contains_in_radius(
        self,
        _center_lat: float,
        _center_lng: float,
        _point_lat: float,
        _point_lng: float,
        _radius_meters: float,
    ):
        raise AssertionError("contains_in_radius should not be called in this test")

    async def golden_time_score(
        self,
        _origin_lat: float,
        _origin_lng: float,
        _emergency_lat: float,
        _emergency_lng: float,
        _average_speed_kmh: float,
        _critical_minutes: float,
    ):
        raise AssertionError("golden_time_score should not be called in this test")

    async def route_risk_score(
        self,
        _traffic_level: float,
        _incident_count: int,
        _weather_severity: float,
        _vulnerable_zone_overlap: float,
        _golden_time_score: float | None,
    ):
        raise AssertionError("route_risk_score should not be called in this test")

    async def nearest_facilities(
        self,
        center_lat: float,
        center_lng: float,
        limit: int,
        district_code: str | None,
    ) -> GeoNearestFacilitiesResult:
        _ = (center_lat, center_lng, limit, district_code)
        return GeoNearestFacilitiesResult(
            items=[
                GeoNearestFacilityItem(
                    source_id="A1",
                    name="Center A",
                    district_code="11110",
                    lat=37.57,
                    lng=126.98,
                    distance_meters=120.5,
                )
            ]
        )


def test_geo_distance_response_shape() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/v1/geo/distance?origin_lat=37.5665&origin_lng=126.9780&target_lat=37.5796&target_lng=126.9770"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["distance_meters"] > 0


def test_geo_geofence_response_shape() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/v1/geo/geofence/contains?center_lat=37.5665&center_lng=126.9780&point_lat=37.5670&point_lng=126.9785&radius_meters=300"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert isinstance(body["data"]["inside"], bool)
    assert body["data"]["distance_meters"] >= 0


def test_geo_golden_time_response_shape() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/v1/geo/golden-time?origin_lat=37.5665&origin_lng=126.9780&emergency_lat=37.5796&emergency_lng=126.9770"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["estimated_minutes"] >= 0
    assert 0 <= body["data"]["score"] <= 100


def test_geo_distance_uses_cache_for_same_query() -> None:
    app = create_app()
    service = CountingGeoService()
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    app.dependency_overrides[get_geo_service] = lambda: service
    app.dependency_overrides[get_facility_cache] = lambda: cache
    client = TestClient(app)

    first = client.get(
        "/v1/geo/distance?origin_lat=37.5665&origin_lng=126.9780&target_lat=37.5796&target_lng=126.9770"
    )
    second = client.get(
        "/v1/geo/distance?origin_lat=37.5665&origin_lng=126.9780&target_lat=37.5796&target_lng=126.9770"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert service.distance_calls == 1


def test_geo_route_risk_response_shape() -> None:
    client = TestClient(create_app())
    response = client.get(
        "/v1/geo/route-risk?traffic_level=0.6&incident_count=2&weather_severity=0.3&vulnerable_zone_overlap=0.2"
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert 0 <= body["data"]["score"] <= 100
    assert body["data"]["level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_geo_nearest_facilities_response_shape() -> None:
    app = create_app()
    service = CountingGeoService()
    cache = FacilityCache(store=InMemoryCacheStore(), ttl_seconds=60)
    app.dependency_overrides[get_geo_service] = lambda: service
    app.dependency_overrides[get_facility_cache] = lambda: cache
    client = TestClient(app)
    response = client.get("/v1/geo/nearest-facilities?center_lat=37.5665&center_lng=126.9780&limit=5")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert len(body["data"]["items"]) == 1
    assert body["data"]["items"][0]["source_id"] == "A1"
