from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FacilityUpsertRequest(BaseModel):
    facility_id: str
    name: str
    district_code: str
    address: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "pipeline"

