from pydantic import BaseModel


class GeoDistanceResult(BaseModel):
    distance_meters: float


class GeoGeofenceResult(BaseModel):
    inside: bool
    distance_meters: float


class GeoGoldenTimeResult(BaseModel):
    estimated_minutes: float
    score: float
