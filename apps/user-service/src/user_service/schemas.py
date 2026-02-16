from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(default="guardian")
    phone: str | None = None
    profile_data: dict[str, Any] = Field(default_factory=dict)


class UserUpdateRequest(BaseModel):
    role: str | None = None
    phone: str | None = None
    profile_data: dict[str, Any] | None = None


class PreferenceUpsertRequest(BaseModel):
    care_type: str = Field(default="senior")
    location_lat: float | None = None
    location_lng: float | None = None
    search_radius_km: int = Field(default=5, ge=1, le=100)
    notification_settings: dict[str, Any] = Field(default_factory=dict)


class InternalUserBootstrapRequest(BaseModel):
    user_id: str = Field(min_length=3, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(default="guardian")
    auth_user_id: str | None = Field(default=None, max_length=255)
    auth_source: str = Field(default="local", max_length=32)
    profile_data: dict[str, Any] = Field(default_factory=dict)
