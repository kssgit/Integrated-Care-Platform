import pytest

from geo_engine.models import GeoPoint
from trust_safety.resident_verification import calculate_geofence_match_score, is_resident_verified


def test_resident_geofence_score_in_range() -> None:
    center = GeoPoint(lat=37.5665, lng=126.9780)
    nearby = GeoPoint(lat=37.5668, lng=126.9782)
    score = calculate_geofence_match_score(center, nearby, radius_meters=200)
    assert 0 <= score <= 100
    assert score > 70


def test_resident_verified_by_threshold() -> None:
    assert is_resident_verified(75.0, threshold=70.0) is True
    assert is_resident_verified(65.0, threshold=70.0) is False


def test_resident_score_invalid_radius() -> None:
    center = GeoPoint(lat=37.5665, lng=126.9780)
    with pytest.raises(ValueError):
        calculate_geofence_match_score(center, center, radius_meters=0)

