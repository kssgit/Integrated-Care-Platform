from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Query, Request

from api.cache import FacilityCache
from api.circuit_breaker import CircuitBreaker, CircuitOpenError
from api.dependencies import get_circuit_breaker, get_facility_cache, get_facility_service, get_rate_limiter
from api.errors import ApiError
from api.rate_limit import SlidingWindowRateLimiter
from api.response import success_response
from api.schemas.facility import FacilityListQuery
from api.services.facility_service import FacilityService

router = APIRouter(prefix="/v1/facilities", tags=["facilities"])


def _resolve_client_key(request: Request) -> str:
    forwarded = request.headers.get("x-client-id")
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host
    return "anonymous"


def _parse_cursor(cursor: str) -> int:
    try:
        value = int(cursor)
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", "cursor must be integer", 422) from exc
    if value < 0:
        raise ApiError("VALIDATION_ERROR", "cursor must be >= 0", 422)
    return value


@router.get("")
async def list_facilities(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    district_code: str | None = None,
    service: FacilityService = Depends(get_facility_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    now = time.time()
    client_key = _resolve_client_key(request)
    allowed = await rate_limiter.allow(client_key, now_seconds=now)
    if not allowed:
        raise ApiError("RATE_LIMIT_EXCEEDED", "Too many requests", 429)

    query = FacilityListQuery(
        page=page,
        page_size=page_size,
        cursor=cursor,
        limit=limit,
        district_code=district_code,
    )
    mode = "cursor" if query.cursor is not None else "page"
    cursor_value = query.cursor or "*"
    cache_key = f"facilities:{mode}:{page}:{page_size}:{cursor_value}:{limit}:{district_code or '*'}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        if query.cursor is not None:
            parsed_cursor = _parse_cursor(query.cursor)
            items, total, next_cursor = await asyncio.wait_for(
                circuit_breaker.call(
                    lambda: service.list_facilities_by_cursor(
                        cursor=parsed_cursor,
                        limit=query.limit,
                        district_code=query.district_code,
                    ),
                    now_seconds=now,
                ),
                timeout=5.0,
            )
        else:
            items, total = await asyncio.wait_for(
                circuit_breaker.call(lambda: service.list_facilities(query), now_seconds=now),
                timeout=5.0,
            )
            next_cursor = None
    except CircuitOpenError as exc:
        raise ApiError("UPSTREAM_UNAVAILABLE", "Please retry later", 503) from exc
    except TimeoutError as exc:
        raise ApiError("UPSTREAM_TIMEOUT", "Upstream timeout", 504) from exc
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError("UPSTREAM_FAILURE", "Upstream request failed", 502) from exc

    meta = {"page": page, "page_size": page_size, "total": total, "next_cursor": next_cursor}
    payload = success_response([item.model_dump() for item in items], meta=meta)
    await cache.set(cache_key, payload)
    return payload
