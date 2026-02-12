import math

from geo_engine.models import GeoPoint

EARTH_RADIUS_METERS = 6_371_000


def haversine_distance_meters(start: GeoPoint, end: GeoPoint) -> float:
    start_lat = math.radians(start.lat)
    end_lat = math.radians(end.lat)
    delta_lat = math.radians(end.lat - start.lat)
    delta_lng = math.radians(end.lng - start.lng)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(start_lat) * math.cos(end_lat) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_METERS * c

