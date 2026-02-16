from __future__ import annotations

from dataclasses import dataclass, field

from devkit.timezone import now_kst_iso
from typing import Any


@dataclass
class UserRecord:
    user_id: str
    email: str
    role: str
    auth_user_id: str | None = None
    auth_source: str = "local"
    status: str = "active"
    phone_encrypted: str | None = None
    phone_hash: str | None = None
    profile_data: dict[str, Any] = field(default_factory=dict)
    deleted_at: str | None = None
    created_at: str = field(default_factory=now_kst_iso)
    updated_at: str = field(default_factory=now_kst_iso)


@dataclass
class UserPreference:
    user_id: str
    care_type: str
    location_lat: float | None = None
    location_lng: float | None = None
    search_radius_km: int = 5
    notification_settings: dict[str, Any] = field(default_factory=dict)
