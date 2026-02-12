from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Query, Request

from api.circuit_breaker import CircuitBreaker, CircuitOpenError
from api.dependencies import get_circuit_breaker, get_facility_service, get_rate_limiter
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


@router.get("")
async def list_facilities(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    district_code: str | None = None,
    service: FacilityService = Depends(get_facility_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> dict:
    now = time.time()
    client_key = _resolve_client_key(request)
    allowed = await rate_limiter.allow(client_key, now_seconds=now)
    if not allowed:
        raise ApiError("RATE_LIMIT_EXCEEDED", "Too many requests", 429)

    query = FacilityListQuery(page=page, page_size=page_size, district_code=district_code)
    try:
        items, total = await asyncio.wait_for(
            circuit_breaker.call(lambda: service.list_facilities(query), now_seconds=now),
            timeout=5.0,
        )
    except CircuitOpenError as exc:
        raise ApiError("UPSTREAM_UNAVAILABLE", "Please retry later", 503) from exc
    except TimeoutError as exc:
        raise ApiError("UPSTREAM_TIMEOUT", "Upstream timeout", 504) from exc
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError("UPSTREAM_FAILURE", "Upstream request failed", 502) from exc

    meta = {"page": page, "page_size": page_size, "total": total}
    return success_response([item.model_dump() for item in items], meta=meta)
