from geo_engine.distance import haversine_distance_meters
from geo_engine.models import GeoPoint


def is_point_inside_radius(center: GeoPoint, point: GeoPoint, radius_meters: float) -> bool:
    if radius_meters < 0:
        raise ValueError("radius_meters must be >= 0")
    return haversine_distance_meters(center, point) <= radius_meters

