from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import Request

from api.errors import ApiError


def service_base_url(env_name: str, default: str = "") -> str:
    return os.getenv(env_name, default).rstrip("/")


async def proxy_request(
    *,
    request: Request,
    base_url: str,
    target_path: str,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    if not base_url:
        raise ApiError("UPSTREAM_UNAVAILABLE", "Service URL not configured", 503)
    url = f"{base_url}{target_path}"
    headers = {}
    for name in ("authorization", "x-trace-id", "x-client-id", "content-type"):
        value = request.headers.get(name)
        if value:
            headers[name] = value
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.request(
                method=request.method,
                url=url,
                params=dict(request.query_params),
                content=body,
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise ApiError("UPSTREAM_TIMEOUT", "Upstream timeout", 504) from exc
    except httpx.HTTPError as exc:
        raise ApiError("UPSTREAM_FAILURE", "Upstream request failed", 502) from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError("UPSTREAM_FAILURE", "Invalid upstream response", 502) from exc
    if response.status_code >= 400:
        error = payload.get("error", {})
        raise ApiError(
            str(error.get("code", "UPSTREAM_FAILURE")),
            str(error.get("message", "Upstream request failed")),
            response.status_code,
        )
    return payload

