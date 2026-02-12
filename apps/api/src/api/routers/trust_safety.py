from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Request

from api.circuit_breaker import CircuitBreaker, CircuitOpenError
from api.dependencies import get_circuit_breaker, get_rate_limiter, get_safe_number_service
from api.errors import ApiError
from api.rate_limit import SlidingWindowRateLimiter
from api.response import success_response
from api.schemas.trust_safety import SafeNumberRouteRequest
from api.services.safe_number_service import SafeNumberService

router = APIRouter(prefix="/v1/trust-safety", tags=["trust-safety"])


def _resolve_client_key(request: Request) -> str:
    forwarded = request.headers.get("x-client-id")
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host
    return "anonymous"


@router.post("/safe-number/route")
async def route_safe_number(
    body: SafeNumberRouteRequest,
    request: Request,
    service: SafeNumberService = Depends(get_safe_number_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> dict:
    now = time.time()
    client_key = _resolve_client_key(request)
    allowed = await rate_limiter.allow(client_key, now_seconds=now)
    if not allowed:
        raise ApiError("RATE_LIMIT_EXCEEDED", "Too many requests", 429)

    try:
        route = await asyncio.wait_for(
            circuit_breaker.call(
                lambda: service.create_route(
                    caller_phone=body.caller_phone,
                    callee_phone=body.callee_phone,
                    ttl_minutes=body.ttl_minutes,
                ),
                now_seconds=now,
            ),
            timeout=5.0,
        )
    except CircuitOpenError as exc:
        raise ApiError("UPSTREAM_UNAVAILABLE", "Please retry later", 503) from exc
    except TimeoutError as exc:
        raise ApiError("UPSTREAM_TIMEOUT", "Upstream timeout", 504) from exc
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError("UPSTREAM_FAILURE", "Safe-number routing failed", 502) from exc

    return success_response(route.model_dump(), meta={})

