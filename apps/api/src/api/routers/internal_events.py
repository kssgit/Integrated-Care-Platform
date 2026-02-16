from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header
from fastapi import Request

from api.cache import FacilityCache
from api.dependencies import get_facility_cache
from api.errors import ApiError
from api.response import success_response
from shared.security import SignatureValidationError, verify_event_signature

router = APIRouter(prefix="/v1/internal/events", tags=["internal-events"])


def _validate_internal_token(header_token: str | None) -> None:
    hmac_secret = os.getenv("INTERNAL_EVENT_HMAC_SECRET")
    expected = os.getenv("INTERNAL_EVENT_TOKEN")
    if not hmac_secret and not expected:
        raise ApiError("INTERNAL_EVENT_AUTH_NOT_CONFIGURED", "Internal event auth is not configured", 503)
    if not expected:
        return
    if not header_token or header_token != expected:
        raise ApiError("UNAUTHORIZED", "Invalid internal token", 401)


def _validate_event_signature(
    *,
    payload: str,
    signature: str | None,
    timestamp: str | None,
) -> None:
    secret = os.getenv("INTERNAL_EVENT_HMAC_SECRET")
    if not secret:
        return
    try:
        verify_event_signature(
            secret=secret,
            payload=payload,
            signature=signature,
            timestamp=timestamp,
        )
    except SignatureValidationError as exc:
        raise ApiError("UNAUTHORIZED", str(exc), 401) from exc


@router.post("")
async def handle_internal_event(
    request: Request,
    event: dict,
    cache: FacilityCache = Depends(get_facility_cache),
    x_internal_token: str | None = Header(default=None),
    x_event_signature: str | None = Header(default=None),
    x_event_timestamp: str | None = Header(default=None),
) -> dict:
    payload_text = (await request.body()).decode("utf-8")
    if os.getenv("INTERNAL_EVENT_HMAC_SECRET"):
        _validate_event_signature(
            payload=payload_text,
            signature=x_event_signature,
            timestamp=x_event_timestamp,
        )
    else:
        _validate_internal_token(x_internal_token)
    event_type = str(event.get("event_type", ""))
    if event_type == "etl_completed":
        invalidated = await cache.invalidate_facilities()
        return success_response({"invalidated_keys": invalidated}, meta={"event_type": event_type})
    return success_response({"ignored": True}, meta={"event_type": event_type})

