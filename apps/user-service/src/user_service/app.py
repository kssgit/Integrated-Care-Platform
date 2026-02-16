from __future__ import annotations

from datetime import datetime, timezone
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from shared.security import (
    InMemoryRevokedTokenStore,
    JWTManager,
    RedisRevokedTokenStore,
    Role,
    encrypt_phone,
    ensure_roles,
)
from user_service.models import UserPreference, UserRecord
from user_service.schemas import PreferenceUpsertRequest, UserCreateRequest, UserUpdateRequest
from user_service.store import UserStore


def success_response(data: object, meta: dict[str, object] | None = None) -> dict[str, object]:
    return {"success": True, "data": data, "meta": meta or {}}


def error_response(code: str, message: str) -> dict[str, object]:
    return {"success": False, "error": {"code": code, "message": message}}


def _build_revoked_store():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return InMemoryRevokedTokenStore()
    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        return RedisRevokedTokenStore(client)
    except Exception:
        return InMemoryRevokedTokenStore()


def create_app() -> FastAPI:
    app = FastAPI(title="User Service", version="0.1.0")
    store = UserStore()
    jwt = JWTManager(secret=os.getenv("JWT_SECRET_KEY", "dev-only-secret"))
    revoked_store = _build_revoked_store()
    encryption_key = os.getenv("ENCRYPTION_MASTER_KEY", "dev-encryption-key")

    async def resolve_auth(authorization: str | None = Header(default=None)) -> dict[str, str]:
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
        return {"user_id": payload.sub, "role": payload.role}

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})
        return JSONResponse(status_code=exc.status_code, content=error_response("HTTP_ERROR", str(exc.detail)))

    @app.get("/healthz")
    async def healthz() -> dict[str, object]:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict[str, object]:
        return success_response({"status": "ready"}, meta={})

    @app.post("/v1/users")
    async def create_user(body: UserCreateRequest, auth: dict[str, str] = Depends(resolve_auth)) -> dict[str, object]:
        if not ensure_roles(auth["role"], {Role.ADMIN, Role.FACILITY_ADMIN}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "insufficient role"})
        user_id = str(uuid4())
        phone_encrypted, phone_hash = encrypt_phone(body.phone, encryption_key)
        user = UserRecord(
            user_id=user_id,
            email=body.email.lower(),
            role=body.role,
            phone_encrypted=phone_encrypted,
            phone_hash=phone_hash,
            profile_data=body.profile_data,
        )
        saved = await store.create_user(user)
        return success_response(saved.__dict__, meta={})

    @app.get("/v1/users/{user_id}")
    async def get_user(
        user_id: str,
        request: Request,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        if auth["user_id"] != user_id and not ensure_roles(auth["role"], {Role.ADMIN, Role.FACILITY_ADMIN}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not allowed"})
        user = await store.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "user not found"})
        await store.add_audit_log(
            actor_user_id=auth["user_id"],
            resource_type="user",
            resource_id=user_id,
            action="read",
            ip_address=request.client.host if request.client else "unknown",
        )
        return success_response(user.__dict__, meta={})

    @app.put("/v1/users/{user_id}")
    async def update_user(
        user_id: str,
        body: UserUpdateRequest,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        if auth["user_id"] != user_id and not ensure_roles(auth["role"], {Role.ADMIN}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not allowed"})
        updates = body.model_dump(exclude_none=True)
        if "phone" in updates:
            phone_encrypted, phone_hash = encrypt_phone(updates.pop("phone"), encryption_key)
            updates["phone_encrypted"] = phone_encrypted
            updates["phone_hash"] = phone_hash
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = await store.update_user(user_id, updates)
        if not updated:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "user not found"})
        return success_response(updated.__dict__, meta={})

    @app.delete("/v1/users/{user_id}")
    async def delete_user(user_id: str, auth: dict[str, str] = Depends(resolve_auth)) -> dict[str, object]:
        if auth["user_id"] != user_id and not ensure_roles(auth["role"], {Role.ADMIN}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not allowed"})
        deleted = await store.soft_delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "user not found"})
        return success_response({"deleted": True}, meta={})

    @app.get("/v1/users/{user_id}/preferences")
    async def get_preferences(user_id: str, auth: dict[str, str] = Depends(resolve_auth)) -> dict[str, object]:
        if auth["user_id"] != user_id and not ensure_roles(auth["role"], {Role.ADMIN, Role.CARE_WORKER}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not allowed"})
        pref = await store.get_preference(user_id)
        return success_response(pref.__dict__ if pref else {}, meta={})

    @app.put("/v1/users/{user_id}/preferences")
    async def upsert_preferences(
        user_id: str,
        body: PreferenceUpsertRequest,
        auth: dict[str, str] = Depends(resolve_auth),
    ) -> dict[str, object]:
        if auth["user_id"] != user_id and not ensure_roles(auth["role"], {Role.ADMIN, Role.CARE_WORKER}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not allowed"})
        pref = UserPreference(user_id=user_id, **body.model_dump())
        saved = await store.set_preference(pref)
        return success_response(saved.__dict__, meta={})

    @app.get("/internal/snapshot")
    async def snapshot(auth: dict[str, str] = Depends(resolve_auth)) -> dict[str, object]:
        if not ensure_roles(auth["role"], {Role.ADMIN}):
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "not allowed"})
        state = await store.snapshot()
        return success_response(state, meta={})

    return app


app = create_app()
