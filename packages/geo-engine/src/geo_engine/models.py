from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lng: float

