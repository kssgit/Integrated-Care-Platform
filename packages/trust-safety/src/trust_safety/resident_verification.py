from geo_engine.distance import haversine_distance_meters
from geo_engine.models import GeoPoint


def calculate_geofence_match_score(
    registered_center: GeoPoint,
    observed_point: GeoPoint,
    radius_meters: float,
) -> float:
    if radius_meters <= 0:
        raise ValueError("radius_meters must be > 0")
    distance = haversine_distance_meters(registered_center, observed_point)
    if distance >= radius_meters:
        return 0.0
    score = 100.0 * (1 - (distance / radius_meters))
    return round(score, 2)


def is_resident_verified(match_score: float, threshold: float = 70.0) -> bool:
    if not 0 <= match_score <= 100:
        raise ValueError("match_score must be in [0, 100]")
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be in [0, 100]")
    return match_score >= threshold

