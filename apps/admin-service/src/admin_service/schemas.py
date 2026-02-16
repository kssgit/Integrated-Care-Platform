from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FacilityPatchRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    metadata: dict[str, Any] | None = None
    reason: str = Field(min_length=1)


class PipelineRunTriggerRequest(BaseModel):
    provider_name: str
    start_page: int = Field(default=1, ge=1)
    end_page: int = Field(default=1, ge=1)
    dry_run: bool = False


class PipelineRunAuditQuery(BaseModel):
    status: str | None = None
    provider: str | None = None
    from_at: datetime | None = None
    to_at: datetime | None = None
