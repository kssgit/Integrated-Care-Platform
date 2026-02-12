from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ProviderEvent:
    trace_id: str
    provider: str
    payload: dict[str, Any]
    timestamp: datetime


@dataclass(frozen=True)
class FacilityRecord:
    source_id: str
    name: str
    address: str
    district_code: str
    lat: float
    lng: float
    source_updated_at: datetime

