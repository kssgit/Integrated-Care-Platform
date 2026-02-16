from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchUpsertRequest(BaseModel):
    document_id: str
    name: str
    district_code: str
    address: str
    metadata: dict[str, Any] = Field(default_factory=dict)

