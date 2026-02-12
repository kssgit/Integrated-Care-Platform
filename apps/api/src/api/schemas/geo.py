from pydantic import BaseModel


class GeoDistanceResult(BaseModel):
    distance_meters: float


class GeoGeofenceResult(BaseModel):
    inside: bool
    distance_meters: float


class GeoGoldenTimeResult(BaseModel):
    estimated_minutes: float
    score: float


class GeoRouteRiskResult(BaseModel):
    score: float
    level: str


class GeoNearestFacilityItem(BaseModel):
    source_id: str
    name: str
    district_code: str
    lat: float
    lng: float
    distance_meters: float


class GeoNearestFacilitiesResult(BaseModel):
    items: list[GeoNearestFacilityItem]
