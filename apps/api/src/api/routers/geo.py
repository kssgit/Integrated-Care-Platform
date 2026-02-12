from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, Query, Request

from api.cache import FacilityCache
from api.circuit_breaker import CircuitBreaker, CircuitOpenError
from api.dependencies import (
    get_circuit_breaker,
    get_facility_cache,
    get_geo_service,
    get_rate_limiter,
)
from api.errors import ApiError
from api.rate_limit import SlidingWindowRateLimiter
from api.response import success_response
from api.services.geo_service import GeoService

router = APIRouter(prefix="/v1/geo", tags=["geo"])


def _resolve_client_key(request: Request) -> str:
    forwarded = request.headers.get("x-client-id")
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host
    return "anonymous"


async def _call_with_guards(
    request: Request,
    cache: FacilityCache,
    rate_limiter: SlidingWindowRateLimiter,
    circuit_breaker: CircuitBreaker,
    cache_key: str,
    action: Callable[[], Awaitable[object]],
) -> dict:
    now = time.time()
    allowed = await rate_limiter.allow(_resolve_client_key(request), now_seconds=now)
    if not allowed:
        raise ApiError("RATE_LIMIT_EXCEEDED", "Too many requests", 429)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        data = await asyncio.wait_for(circuit_breaker.call(action, now_seconds=now), timeout=5.0)
    except CircuitOpenError as exc:
        raise ApiError("UPSTREAM_UNAVAILABLE", "Please retry later", 503) from exc
    except TimeoutError as exc:
        raise ApiError("UPSTREAM_TIMEOUT", "Upstream timeout", 504) from exc
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", str(exc), 422) from exc
    except Exception as exc:
        raise ApiError("UPSTREAM_FAILURE", "Geo service failed", 502) from exc
    payload = success_response(data.model_dump(), meta={})
    await cache.set(cache_key, payload)
    return payload


@router.get("/distance")
async def distance(
    request: Request,
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    target_lat: float = Query(..., ge=-90, le=90),
    target_lng: float = Query(..., ge=-180, le=180),
    service: GeoService = Depends(get_geo_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    cache_key = f"geo:distance:{origin_lat}:{origin_lng}:{target_lat}:{target_lng}"
    return await _call_with_guards(
        request=request,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        cache_key=cache_key,
        action=lambda: service.distance_meters(origin_lat, origin_lng, target_lat, target_lng),
    )


@router.get("/geofence/contains")
async def contains_in_radius(
    request: Request,
    center_lat: float = Query(..., ge=-90, le=90),
    center_lng: float = Query(..., ge=-180, le=180),
    point_lat: float = Query(..., ge=-90, le=90),
    point_lng: float = Query(..., ge=-180, le=180),
    radius_meters: float = Query(..., ge=0),
    service: GeoService = Depends(get_geo_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    cache_key = f"geo:geofence:{center_lat}:{center_lng}:{point_lat}:{point_lng}:{radius_meters}"
    return await _call_with_guards(
        request=request,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        cache_key=cache_key,
        action=lambda: service.contains_in_radius(
            center_lat,
            center_lng,
            point_lat,
            point_lng,
            radius_meters,
        ),
    )


@router.get("/golden-time")
async def golden_time_score(
    request: Request,
    origin_lat: float = Query(..., ge=-90, le=90),
    origin_lng: float = Query(..., ge=-180, le=180),
    emergency_lat: float = Query(..., ge=-90, le=90),
    emergency_lng: float = Query(..., ge=-180, le=180),
    average_speed_kmh: float = Query(default=30.0, gt=0),
    critical_minutes: float = Query(default=20.0, gt=0),
    service: GeoService = Depends(get_geo_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    cache_key = (
        f"geo:golden-time:{origin_lat}:{origin_lng}:{emergency_lat}:{emergency_lng}:"
        f"{average_speed_kmh}:{critical_minutes}"
    )
    return await _call_with_guards(
        request=request,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        cache_key=cache_key,
        action=lambda: service.golden_time_score(
            origin_lat,
            origin_lng,
            emergency_lat,
            emergency_lng,
            average_speed_kmh,
            critical_minutes,
        ),
    )


@router.get("/route-risk")
async def route_risk(
    request: Request,
    traffic_level: float = Query(..., ge=0, le=1),
    incident_count: int = Query(default=0, ge=0),
    weather_severity: float = Query(..., ge=0, le=1),
    vulnerable_zone_overlap: float = Query(..., ge=0, le=1),
    golden_time_score: float | None = Query(default=None, ge=0, le=100),
    service: GeoService = Depends(get_geo_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    cache_key = (
        f"geo:route-risk:{traffic_level}:{incident_count}:{weather_severity}:"
        f"{vulnerable_zone_overlap}:{golden_time_score}"
    )
    return await _call_with_guards(
        request=request,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        cache_key=cache_key,
        action=lambda: service.route_risk_score(
            traffic_level=traffic_level,
            incident_count=incident_count,
            weather_severity=weather_severity,
            vulnerable_zone_overlap=vulnerable_zone_overlap,
            golden_time_score=golden_time_score,
        ),
    )


@router.get("/nearest-facilities")
async def nearest_facilities(
    request: Request,
    center_lat: float = Query(..., ge=-90, le=90),
    center_lng: float = Query(..., ge=-180, le=180),
    limit: int = Query(default=5, ge=1, le=100),
    district_code: str | None = None,
    service: GeoService = Depends(get_geo_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
    cache: FacilityCache = Depends(get_facility_cache),
) -> dict:
    cache_key = f"geo:nearest:{center_lat}:{center_lng}:{limit}:{district_code or '*'}"
    return await _call_with_guards(
        request=request,
        cache=cache,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        cache_key=cache_key,
        action=lambda: service.nearest_facilities(
            center_lat=center_lat,
            center_lng=center_lng,
            limit=limit,
            district_code=district_code,
        ),
    )
