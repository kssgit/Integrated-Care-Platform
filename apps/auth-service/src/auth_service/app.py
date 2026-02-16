from __future__ import annotations

import os
import time
from uuid import uuid4

from devkit.config import load_settings
from devkit.redis import create_redis_client, create_revoked_token_store
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from auth_service.rate_limit import SlidingWindowLimiter
from auth_service.response import error_response, success_response
from auth_service.schemas import LoginRequest, LogoutRequest, RefreshRequest
from shared.security import (
    JWTManager,
    RevokedTokenStore,
)


def _build_revoked_store() -> RevokedTokenStore:
    settings = load_settings("auth-service")
    return create_revoked_token_store(create_redis_client(settings.REDIS_URL))


def _load_static_users() -> dict[str, dict[str, str]]:
    default_users = {
        "test@example.com": {"password": "password123", "role": "guardian"},
        "admin@example.com": {"password": "password123", "role": "admin"},
    }
    raw = os.getenv("AUTH_STATIC_USERS_JSON")
    if not raw:
        return default_users
    try:
        import json

        parsed = json.loads(raw)
        users = {
            str(item["email"]).lower(): {
                "password": str(item["password"]),
                "role": str(item["role"]),
            }
            for item in parsed
        }
        return users or default_users
    except Exception:
        return default_users


def create_app() -> FastAPI:
    settings = load_settings("auth-service")
    app = FastAPI(title="Auth Service", version="0.1.0")
    jwt = JWTManager(secret=settings.JWT_SECRET_KEY)
    revoked_store = _build_revoked_store()
    users = _load_static_users()
    login_limiter = SlidingWindowLimiter(limit=5, window_seconds=300)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            payload = {"success": False, "error": exc.detail}
        else:
            payload = error_response("HTTP_ERROR", str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.get("/healthz")
    async def healthz() -> dict:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict:
        return success_response({"status": "ready"}, meta={})

    @app.post("/v1/auth/login")
    async def login(body: LoginRequest, request: Request) -> dict:
        client_ip = request.client.host if request.client else "anonymous"
        if not login_limiter.allow(client_ip, now_seconds=time.time()):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Too many login attempts"},
            )
        user_id = body.email.lower()
        user = users.get(user_id)
        if not user or user["password"] != body.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"},
            )
        role = user["role"]
        token_jti = str(uuid4())
        access_token = jwt.issue_access_token(user_id, role, token_jti)
        refresh_token = jwt.issue_refresh_token(user_id, role, token_jti)
        return success_response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in_seconds": 15 * 60,
            },
            meta={},
        )

    @app.post("/v1/auth/refresh")
    async def refresh(body: RefreshRequest) -> dict:
        try:
            payload = jwt.decode(body.refresh_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": str(exc)},
            ) from exc
        if payload.typ != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "refresh token required"},
            )
        if await revoked_store.is_revoked(payload.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "token has been revoked"},
            )
        access_token = jwt.issue_access_token(payload.sub, payload.role, payload.jti)
        return success_response({"access_token": access_token, "token_type": "bearer"}, meta={})

    @app.post("/v1/auth/logout")
    async def logout(body: LogoutRequest) -> dict:
        try:
            payload = jwt.decode(body.refresh_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": str(exc)},
            ) from exc
        ttl = max(payload.exp - int(time.time()), 0)
        await revoked_store.revoke(payload.jti, ttl_seconds=ttl)
        return success_response({"revoked": True}, meta={})

    @app.get("/v1/auth/me")
    async def me(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "missing bearer token"},
            )
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": str(exc)},
            ) from exc
        if await revoked_store.is_revoked(payload.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "TOKEN_REVOKED", "message": "token has been revoked"},
            )
        return success_response({"user_id": payload.sub, "role": payload.role}, meta={})

    return app


app = create_app()
