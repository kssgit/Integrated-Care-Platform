from __future__ import annotations

from typing import Any

from devkit.config import load_settings
from devkit.redis import create_redis_client, create_revoked_token_store
from fastapi import Header

from api.errors import ApiError
from shared.security import (
    JWTManager,
    Role,
    ensure_roles,
)

settings = load_settings("integrated-care-api")
_jwt = JWTManager(secret=settings.JWT_SECRET_KEY)


def _build_revoked_store():
    return create_revoked_token_store(create_redis_client(settings.REDIS_URL))


_revoked_store = _build_revoked_store()


async def validate_bearer_token(authorization: str | None) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError("UNAUTHORIZED", "Missing bearer token", 401)
    token = authorization.split(" ", 1)[1]
    try:
        payload = _jwt.decode(token)
    except ValueError as exc:
        raise ApiError("UNAUTHORIZED", str(exc), 401) from exc
    if payload.typ != "access":
        raise ApiError("UNAUTHORIZED", "Access token required", 401)
    if await _revoked_store.is_revoked(payload.jti):
        raise ApiError("UNAUTHORIZED", "Token has been revoked", 401)
    return {"user_id": payload.sub, "role": payload.role, "jti": payload.jti}


async def require_authenticated(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return await validate_bearer_token(authorization)


def require_roles(auth: dict[str, Any], allowed: set[Role]) -> None:
    if not ensure_roles(str(auth.get("role", "")), allowed):
        raise ApiError("FORBIDDEN", "Not enough permissions", 403)
