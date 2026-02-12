import pytest

from geo_engine.golden_time import calculate_golden_time_score, estimate_travel_minutes
from geo_engine.models import GeoPoint


def test_estimate_travel_minutes() -> None:
    minutes = estimate_travel_minutes(distance_meters=10_000, average_speed_kmh=30)
    assert round(minutes, 2) == 20.0


def test_calculate_golden_time_score_range() -> None:
    origin = GeoPoint(lat=37.5665, lng=126.9780)
    emergency_room = GeoPoint(lat=37.5700, lng=126.9900)
    minutes, score = calculate_golden_time_score(origin, emergency_room)
    assert minutes >= 0
    assert 0 <= score <= 100


def test_estimate_travel_minutes_invalid_speed() -> None:
    with pytest.raises(ValueError):
        estimate_travel_minutes(distance_meters=1000, average_speed_kmh=0)

