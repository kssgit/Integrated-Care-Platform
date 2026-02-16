from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from user_service.models import UserPreference, UserRecord


class UserStore:
    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}
        self._preferences: dict[str, UserPreference] = {}
        self._audit_logs: list[dict[str, Any]] = []

    async def create_user(self, user: UserRecord) -> UserRecord:
        self._users[user.user_id] = user
        return user

    async def get_user(self, user_id: str) -> UserRecord | None:
        return self._users.get(user_id)

    async def update_user(self, user_id: str, updates: dict[str, Any]) -> UserRecord | None:
        user = self._users.get(user_id)
        if not user:
            return None
        for key, value in updates.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        user.updated_at = datetime.now(timezone.utc).isoformat()
        return user

    async def soft_delete_user(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if not user:
            return False
        now = datetime.now(timezone.utc).isoformat()
        user.deleted_at = now
        user.updated_at = now
        return True

    async def set_preference(self, preference: UserPreference) -> UserPreference:
        self._preferences[preference.user_id] = preference
        return preference

    async def get_preference(self, user_id: str) -> UserPreference | None:
        return self._preferences.get(user_id)

    async def add_audit_log(
        self,
        *,
        actor_user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
    ) -> None:
        self._audit_logs.append(
            {
                "actor_user_id": actor_user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "ip_address": ip_address,
                "accessed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def snapshot(self) -> dict[str, Any]:
        return {
            "users": [asdict(item) for item in self._users.values()],
            "preferences": [asdict(item) for item in self._preferences.values()],
            "audit_logs": list(self._audit_logs),
        }

