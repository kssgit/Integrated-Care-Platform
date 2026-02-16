from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from api.proxy import proxy_request, service_base_url
from api.security import require_authenticated

router = APIRouter(prefix="/v1/users", tags=["users-gateway"])


@router.post("")
async def create_user(request: Request, _: dict[str, Any] = Depends(require_authenticated)) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("USER_SERVICE_BASE_URL"),
        target_path="/v1/users",
    )


@router.get("/{user_id}")
async def get_user(user_id: str, request: Request, _: dict[str, Any] = Depends(require_authenticated)) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("USER_SERVICE_BASE_URL"),
        target_path=f"/v1/users/{user_id}",
    )


@router.put("/{user_id}")
async def update_user(user_id: str, request: Request, _: dict[str, Any] = Depends(require_authenticated)) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("USER_SERVICE_BASE_URL"),
        target_path=f"/v1/users/{user_id}",
    )


@router.delete("/{user_id}")
async def delete_user(user_id: str, request: Request, _: dict[str, Any] = Depends(require_authenticated)) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("USER_SERVICE_BASE_URL"),
        target_path=f"/v1/users/{user_id}",
    )


@router.get("/{user_id}/preferences")
async def get_preferences(
    user_id: str,
    request: Request,
    _: dict[str, Any] = Depends(require_authenticated),
) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("USER_SERVICE_BASE_URL"),
        target_path=f"/v1/users/{user_id}/preferences",
    )


@router.put("/{user_id}/preferences")
async def upsert_preferences(
    user_id: str,
    request: Request,
    _: dict[str, Any] = Depends(require_authenticated),
) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("USER_SERVICE_BASE_URL"),
        target_path=f"/v1/users/{user_id}/preferences",
    )

