from geo_engine.distance import haversine_distance_meters
from geo_engine.models import GeoPoint


def test_haversine_distance_is_zero_for_same_point() -> None:
    point = GeoPoint(lat=37.5665, lng=126.9780)
    distance = haversine_distance_meters(point, point)
    assert distance == 0.0


def test_haversine_distance_is_positive_for_different_points() -> None:
    city_hall = GeoPoint(lat=37.5665, lng=126.9780)
    gangnam = GeoPoint(lat=37.4979, lng=127.0276)
    distance = haversine_distance_meters(city_hall, gangnam)
    assert distance > 0
    assert distance < 20_000

