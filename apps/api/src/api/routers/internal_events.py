from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header

from api.cache import FacilityCache
from api.dependencies import get_facility_cache
from api.errors import ApiError
from api.response import success_response

router = APIRouter(prefix="/v1/internal/events", tags=["internal-events"])


def _validate_internal_token(header_token: str | None) -> None:
    expected = os.getenv("INTERNAL_EVENT_TOKEN")
    if not expected:
        return
    if not header_token or header_token != expected:
        raise ApiError("UNAUTHORIZED", "Invalid internal token", 401)


@router.post("")
async def handle_internal_event(
    event: dict,
    cache: FacilityCache = Depends(get_facility_cache),
    x_internal_token: str | None = Header(default=None),
) -> dict:
    _validate_internal_token(x_internal_token)
    event_type = str(event.get("event_type", ""))
    if event_type == "etl_completed":
        invalidated = await cache.invalidate_facilities()
        return success_response({"invalidated_keys": invalidated}, meta={"event_type": event_type})
    return success_response({"ignored": True}, meta={"event_type": event_type})

