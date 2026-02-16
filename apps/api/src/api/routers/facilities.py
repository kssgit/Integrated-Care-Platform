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
from api.proxy import proxy_request, service_base_url

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


async def _local_fetch_all(service: FacilityService) -> list:
    query = FacilityListQuery(page=1, page_size=100, district_code=None)
    items, _ = await service.list_facilities(query)
    return items


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
    facility_service_url = service_base_url("FACILITY_SERVICE_BASE_URL")
    if facility_service_url:
        return await proxy_request(
            request=request,
            base_url=facility_service_url,
            target_path="/v1/facilities",
        )

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


@router.get("/{facility_id}")
async def get_facility_detail(
    facility_id: str,
    request: Request,
    service: FacilityService = Depends(get_facility_service),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    facility_service_url = service_base_url("FACILITY_SERVICE_BASE_URL")
    if facility_service_url:
        return await proxy_request(
            request=request,
            base_url=facility_service_url,
            target_path=f"/v1/facilities/{facility_id}",
        )
    cache_key = f"facilities:detail:{facility_id}"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    items = await _local_fetch_all(service)
    matched = next((item for item in items if item.id == facility_id), None)
    if matched is None:
        raise ApiError("NOT_FOUND", "Facility not found", 404)
    payload = success_response(matched.model_dump(), meta={})
    await cache.set(cache_key, payload)
    return payload


@router.get("/search")
async def search_facilities(
    request: Request,
    query: str = Query(..., min_length=1),
    district_code: str | None = None,
    service: FacilityService = Depends(get_facility_service),
) -> dict:
    facility_service_url = service_base_url("FACILITY_SERVICE_BASE_URL")
    if facility_service_url:
        return await proxy_request(
            request=request,
            base_url=facility_service_url,
            target_path="/v1/facilities/search",
        )
    query_lower = query.lower()
    items = await _local_fetch_all(service)
    data = [
        item.model_dump()
        for item in items
        if (not district_code or item.district_code == district_code) and query_lower in item.name.lower()
    ]
    return success_response(data, meta={"count": len(data)})
