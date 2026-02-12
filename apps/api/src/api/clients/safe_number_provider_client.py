from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from api.errors import ApiError


class SafeNumberProviderClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client_factory = client_factory

    async def allocate(self, caller_phone: str, callee_phone: str, ttl_minutes: int) -> str:
        payload = {
            "caller_phone": caller_phone,
            "callee_phone": callee_phone,
            "ttl_minutes": ttl_minutes,
        }
        try:
            factory = self._client_factory or (lambda: httpx.AsyncClient(timeout=self._timeout_seconds))
            async with factory() as client:
                response = await client.post(f"{self._base_url}/safe-number/allocate", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ApiError("UPSTREAM_TIMEOUT", "Safe-number provider timeout", 504) from exc
        except httpx.HTTPError as exc:
            raise ApiError("UPSTREAM_FAILURE", "Safe-number provider failure", 502) from exc

        data = response.json()
        relay_number = data.get("relay_number")
        if not isinstance(relay_number, str):
            raise ApiError("UPSTREAM_FAILURE", "Invalid safe-number provider response", 502)
        return relay_number

