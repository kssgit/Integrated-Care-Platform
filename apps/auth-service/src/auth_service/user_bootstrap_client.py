from __future__ import annotations

import asyncio
from typing import Any

import httpx


class UserBootstrapClient:
    def __init__(
        self,
        *,
        base_url: str | None,
        internal_token: str,
        timeout_seconds: float = 4.0,
    ) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._internal_token = internal_token
        self._timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self._base_url and self._internal_token)

    async def ensure_user(
        self,
        *,
        user_id: str,
        email: str,
        role: str,
        auth_user_id: str | None = None,
        auth_source: str = "local",
        profile_data: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "auth_user_id": auth_user_id or user_id,
            "auth_source": auth_source,
            "profile_data": profile_data or {},
        }
        attempts = 3
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.post(
                        f"{self._base_url}/internal/users/bootstrap",
                        headers={"x-internal-token": self._internal_token},
                        json=payload,
                    )
                response.raise_for_status()
                return
            except Exception:
                if attempt == attempts - 1:
                    raise
                await asyncio.sleep(0.2 * (2**attempt))
