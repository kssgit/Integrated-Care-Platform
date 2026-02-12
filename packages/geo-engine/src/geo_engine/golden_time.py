from geo_engine.distance import haversine_distance_meters
from geo_engine.models import GeoPoint


def estimate_travel_minutes(distance_meters: float, average_speed_kmh: float) -> float:
    if average_speed_kmh <= 0:
        raise ValueError("average_speed_kmh must be > 0")
    meters_per_minute = (average_speed_kmh * 1000) / 60
    return distance_meters / meters_per_minute


def calculate_golden_time_score(
    origin: GeoPoint,
    emergency_room: GeoPoint,
    average_speed_kmh: float = 30.0,
    critical_minutes: float = 20.0,
) -> tuple[float, float]:
    distance_meters = haversine_distance_meters(origin, emergency_room)
    estimated_minutes = estimate_travel_minutes(distance_meters, average_speed_kmh)
    if critical_minutes <= 0:
        raise ValueError("critical_minutes must be > 0")
    raw_score = max(0.0, 100.0 * (1 - (estimated_minutes / critical_minutes)))
    return round(estimated_minutes, 2), round(raw_score, 2)

