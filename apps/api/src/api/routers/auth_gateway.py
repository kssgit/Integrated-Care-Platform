from __future__ import annotations

from fastapi import APIRouter, Request

from api.proxy import proxy_request, service_base_url

router = APIRouter(prefix="/v1/auth", tags=["auth-gateway"])


@router.post("/login")
async def login(request: Request) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("AUTH_SERVICE_BASE_URL"),
        target_path="/v1/auth/login",
    )


@router.post("/refresh")
async def refresh(request: Request) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("AUTH_SERVICE_BASE_URL"),
        target_path="/v1/auth/refresh",
    )


@router.post("/logout")
async def logout(request: Request) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("AUTH_SERVICE_BASE_URL"),
        target_path="/v1/auth/logout",
    )


@router.get("/me")
async def me(request: Request) -> dict:
    return await proxy_request(
        request=request,
        base_url=service_base_url("AUTH_SERVICE_BASE_URL"),
        target_path="/v1/auth/me",
    )

