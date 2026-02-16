from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FacilityPatchRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    metadata: dict[str, Any] | None = None
    reason: str = Field(min_length=1)


class PipelineRunTriggerRequest(BaseModel):
    provider_name: Literal[
        "seoul_open_data",
        "seoul_district_open_data",
        "gyeonggi_open_data",
        "national_open_data",
        "mohw_open_data",
    ]
    start_page: int = Field(default=1, ge=1)
    end_page: int = Field(default=1, ge=1)
    dry_run: bool = False

    @model_validator(mode="after")
    def validate_page_range(self) -> "PipelineRunTriggerRequest":
        if self.end_page < self.start_page:
            raise ValueError("end_page must be greater than or equal to start_page")
        return self


class PipelineRunAuditQuery(BaseModel):
    status: str | None = None
    provider: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
