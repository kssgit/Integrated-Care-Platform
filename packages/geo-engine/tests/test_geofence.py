import pytest

from geo_engine.geofence import is_point_inside_radius
from geo_engine.models import GeoPoint


def test_point_inside_radius() -> None:
    center = GeoPoint(lat=37.5665, lng=126.9780)
    nearby = GeoPoint(lat=37.5670, lng=126.9784)
    assert is_point_inside_radius(center, nearby, radius_meters=100)


def test_point_outside_radius() -> None:
    center = GeoPoint(lat=37.5665, lng=126.9780)
    far = GeoPoint(lat=37.4979, lng=127.0276)
    assert not is_point_inside_radius(center, far, radius_meters=100)


def test_negative_radius_raises() -> None:
    center = GeoPoint(lat=37.5665, lng=126.9780)
    point = GeoPoint(lat=37.5665, lng=126.9780)
    with pytest.raises(ValueError):
        is_point_inside_radius(center, point, radius_meters=-1)

