from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from api.errors import ApiError


class FacilityProviderClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._client_factory = client_factory

    async def fetch_facilities(
        self,
        page: int,
        page_size: int,
        district_code: str | None,
    ) -> tuple[list[dict[str, Any]], int]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if district_code:
            params["district_code"] = district_code

        try:
            factory = self._client_factory or (lambda: httpx.AsyncClient(timeout=self._timeout_seconds))
            async with factory() as client:
                response = await client.get(f"{self._base_url}/facilities", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ApiError("UPSTREAM_TIMEOUT", "Upstream timeout", 504) from exc
        except httpx.HTTPStatusError as exc:
            raise ApiError("UPSTREAM_HTTP_ERROR", "Upstream returned error", 502) from exc
        except httpx.HTTPError as exc:
            raise ApiError("UPSTREAM_FAILURE", "Upstream request failed", 502) from exc

        payload = response.json()
        data = payload.get("data", [])
        meta = payload.get("meta", {})
        total = int(meta.get("total", len(data)))
        return data, total
