from __future__ import annotations

from geo_engine.distance import haversine_distance_meters
from geo_engine.geofence import is_point_inside_radius
from geo_engine.golden_time import calculate_golden_time_score
from geo_engine.models import GeoPoint

from api.schemas.geo import GeoDistanceResult, GeoGeofenceResult, GeoGoldenTimeResult


class GeoService:
    async def distance_meters(
        self,
        origin_lat: float,
        origin_lng: float,
        target_lat: float,
        target_lng: float,
    ) -> GeoDistanceResult:
        origin = GeoPoint(lat=origin_lat, lng=origin_lng)
        target = GeoPoint(lat=target_lat, lng=target_lng)
        distance_meters = haversine_distance_meters(origin, target)
        return GeoDistanceResult(distance_meters=round(distance_meters, 2))

    async def contains_in_radius(
        self,
        center_lat: float,
        center_lng: float,
        point_lat: float,
        point_lng: float,
        radius_meters: float,
    ) -> GeoGeofenceResult:
        center = GeoPoint(lat=center_lat, lng=center_lng)
        point = GeoPoint(lat=point_lat, lng=point_lng)
        distance_meters = haversine_distance_meters(center, point)
        inside = is_point_inside_radius(center=center, point=point, radius_meters=radius_meters)
        return GeoGeofenceResult(inside=inside, distance_meters=round(distance_meters, 2))

    async def golden_time_score(
        self,
        origin_lat: float,
        origin_lng: float,
        emergency_lat: float,
        emergency_lng: float,
        average_speed_kmh: float,
        critical_minutes: float,
    ) -> GeoGoldenTimeResult:
        origin = GeoPoint(lat=origin_lat, lng=origin_lng)
        emergency = GeoPoint(lat=emergency_lat, lng=emergency_lng)
        estimated_minutes, score = calculate_golden_time_score(
            origin=origin,
            emergency_room=emergency,
            average_speed_kmh=average_speed_kmh,
            critical_minutes=critical_minutes,
        )
        return GeoGoldenTimeResult(estimated_minutes=estimated_minutes, score=score)
