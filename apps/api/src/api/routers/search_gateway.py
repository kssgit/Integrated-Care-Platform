from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from api.proxy import proxy_request, service_base_url
from api.security import require_authenticated

router = APIRouter(prefix="/v1/search", tags=["search-gateway"])


@router.get("/facilities")
async def search_facilities(request: Request, _: dict[str, Any] = Depends(require_authenticated)) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("SEARCH_SERVICE_BASE_URL"),
        target_path="/v1/search/facilities",
    )

