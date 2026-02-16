from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class UserRecord:
    user_id: str
    email: str
    role: str
    phone_encrypted: str | None = None
    phone_hash: str | None = None
    profile_data: dict[str, Any] = field(default_factory=dict)
    deleted_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UserPreference:
    user_id: str
    care_type: str
    location_lat: float | None = None
    location_lng: float | None = None
    search_radius_km: int = 5
    notification_settings: dict[str, Any] = field(default_factory=dict)

