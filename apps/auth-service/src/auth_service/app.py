from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from devkit.config import load_settings
from devkit.observability import configure_probe_access_log_filter
from devkit.redis import create_redis_client, create_revoked_token_store
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from auth_service.rate_limit import SlidingWindowLimiter
from auth_service.response import error_response, success_response
from auth_service.schemas import LoginRequest, LogoutRequest, RefreshRequest, SSOCallbackRequest, SignupRequest
from auth_service.sso import create_sso_client_from_env
from auth_service.store import AuthStore, UserAlreadyExistsError
from auth_service.user_bootstrap_client import UserBootstrapClient
from shared.security import JWTManager, Role, RevokedTokenStore, ensure_roles


def _build_revoked_store() -> RevokedTokenStore:
    settings = load_settings("auth-service")
    return create_revoked_token_store(create_redis_client(settings.REDIS_URL))


def _load_bootstrap_users() -> dict[str, dict[str, str]]:
    default_users = {
        "test@example.com": {"password": "password123", "role": "guardian"},
        "admin@example.com": {"password": "password123", "role": "admin"},
    }
    raw = os.getenv("AUTH_STATIC_USERS_JSON")
    if not raw:
        return default_users
    try:
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


def _issue_tokens(jwt: JWTManager, *, user_id: str, role: str) -> dict[str, str | int]:
    token_jti = str(uuid4())
    access_token = jwt.issue_access_token(user_id, role, token_jti)
    refresh_token = jwt.issue_refresh_token(user_id, role, token_jti)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": 15 * 60,
    }


def create_app() -> FastAPI:
    settings = load_settings("auth-service")
    jwt = JWTManager(secret=settings.JWT_SECRET_KEY)
    revoked_store = _build_revoked_store()
    login_limiter = SlidingWindowLimiter(limit=5, window_seconds=300)
    sso_mock_enabled = os.getenv("AUTH_SSO_MOCK_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    sso_client = create_sso_client_from_env()
    auth_store = AuthStore(database_url=settings.DATABASE_URL, bootstrap_users=_load_bootstrap_users())
    user_bootstrap = UserBootstrapClient(
        base_url=settings.USER_SERVICE_BASE_URL,
        internal_token=settings.INTERNAL_EVENT_HMAC_SECRET,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await auth_store.ensure_ready()
        try:
            yield
        finally:
            await auth_store.close()

    app = FastAPI(title="Auth Service", version="0.1.0", lifespan=lifespan)
    configure_probe_access_log_filter()

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

    @app.get("/dev/auth-test", response_class=HTMLResponse)
    async def auth_test_page() -> str:
        return """
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Auth Test</title>
    <style>
      body { font-family: sans-serif; max-width: 760px; margin: 24px auto; padding: 0 12px; }
      input, button, textarea { width: 100%; margin-top: 8px; padding: 8px; box-sizing: border-box; }
      button { cursor: pointer; }
      .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .muted { color: #666; font-size: 13px; }
      pre { background: #111; color: #eaeaea; padding: 12px; border-radius: 8px; overflow: auto; }
    </style>
  </head>
  <body>
    <h1>Auth Service Test</h1>
    <p class="muted">Swagger: <a href="/docs" target="_blank">/docs</a></p>
    <div>
      <label>Email</label>
      <input id="email" value="test@example.com" />
      <label>Password</label>
      <input id="password" value="password123" />
      <div class="row">
        <button onclick="signup()">Signup</button>
        <button onclick="login()">Login</button>
      </div>
      <div class="row">
        <button onclick="me()">Me</button>
        <button onclick="refresh()">Refresh</button>
      </div>
      <button onclick="logout()">Logout</button>
      <div class="row">
        <button onclick="ssoAuthorize('google')">Google SSO Authorize</button>
        <button onclick="ssoAuthorize('naver')">Naver SSO Authorize</button>
      </div>
    </div>
    <label>Access Token</label>
    <textarea id="access" rows="4"></textarea>
    <label>Refresh Token</label>
    <textarea id="refreshToken" rows="4"></textarea>
    <h3>Response</h3>
    <pre id="out">ready</pre>
    <script>
      async function req(path, method, body, withAuth=false) {
        const headers = { "Content-Type": "application/json" };
        if (withAuth) headers["Authorization"] = "Bearer " + document.getElementById("access").value.trim();
        const res = await fetch(path, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined
        });
        const text = await res.text();
        document.getElementById("out").textContent = `HTTP ${res.status}\\n${text}`;
        try { return JSON.parse(text); } catch { return null; }
      }
      async function login() {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const data = await req("/v1/auth/login", "POST", { email, password, role: "guardian" });
        if (data && data.success) {
          document.getElementById("access").value = data.data.access_token || "";
          document.getElementById("refreshToken").value = data.data.refresh_token || "";
        }
      }
      async function signup() {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const data = await req("/v1/auth/signup", "POST", { email, password, role: "guardian" });
        if (data && data.success) {
          document.getElementById("access").value = data.data.access_token || "";
          document.getElementById("refreshToken").value = data.data.refresh_token || "";
        }
      }
      async function me() {
        await req("/v1/auth/me", "GET", null, true);
      }
      async function refresh() {
        const refreshToken = document.getElementById("refreshToken").value.trim();
        const data = await req("/v1/auth/refresh", "POST", { refresh_token: refreshToken });
        if (data && data.success) {
          document.getElementById("access").value = data.data.access_token || "";
        }
      }
      async function logout() {
        const refreshToken = document.getElementById("refreshToken").value.trim();
        await req("/v1/auth/logout", "POST", { refresh_token: refreshToken });
      }
      async function ssoAuthorize(provider) {
        const redirectUri = window.location.origin + "/dev/auth-test";
        await req(`/v1/auth/sso/${provider}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`, "GET");
      }
    </script>
  </body>
</html>
        """

    @app.post("/v1/auth/login")
    async def login(body: LoginRequest, request: Request) -> dict:
        client_ip = request.client.host if request.client else "anonymous"
        if not login_limiter.allow(client_ip, now_seconds=time.time()):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Too many login attempts"},
            )
        user = await auth_store.authenticate_local(email=body.email, password=body.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "invalid email or password"},
            )
        return success_response(
            {"user_id": user.user_id, **_issue_tokens(jwt, user_id=user.user_id, role=user.role)},
            meta={},
        )

    @app.post("/v1/auth/signup")
    async def signup(body: SignupRequest) -> dict:
        if not ensure_roles(body.role, {role for role in Role}):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_ROLE", "message": "invalid role value"},
            )
        try:
            user = await auth_store.signup_local(email=body.email, password=body.password, role=body.role)
        except UserAlreadyExistsError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "USER_ALREADY_EXISTS", "message": str(exc)},
            ) from exc
        await user_bootstrap.ensure_user(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            auth_user_id=user.user_id,
            auth_source=user.auth_source,
            profile_data={},
        )
        return success_response(
            {"user_id": user.user_id, **_issue_tokens(jwt, user_id=user.user_id, role=user.role)},
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
        user = await auth_store.get_user_by_id(payload.sub)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "user no longer exists"},
            )
        access_token = jwt.issue_access_token(payload.sub, user.role, payload.jti)
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
        user = await auth_store.get_user_by_id(payload.sub)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHORIZED", "message": "user not found"},
            )
        return success_response({"user_id": user.user_id, "role": user.role}, meta={})

    @app.get("/v1/auth/sso/{provider}/authorize")
    async def sso_authorize(provider: str, redirect_uri: str) -> dict:
        provider_key = provider.lower()
        if provider_key not in sso_client.supported_providers():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "UNSUPPORTED_SSO_PROVIDER", "message": "provider is not supported"},
            )
        state = str(uuid4())
        authorization_url = sso_client.build_authorize_url(provider_key, redirect_uri=redirect_uri, state=state)
        if not authorization_url:
            return success_response(
                {
                    "provider": provider_key,
                    "state": state,
                    "configured": False,
                    "authorization_url": None,
                    "message": "SSO provider env is not configured",
                },
                meta={},
            )
        return success_response(
            {
                "provider": provider_key,
                "state": state,
                "configured": True,
                "authorization_url": authorization_url,
            },
            meta={},
        )

    @app.post("/v1/auth/sso/{provider}/callback")
    async def sso_callback(provider: str, body: SSOCallbackRequest) -> dict:
        provider_key = provider.lower()
        if provider_key not in sso_client.supported_providers():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "UNSUPPORTED_SSO_PROVIDER", "message": "provider is not supported"},
            )

        if sso_mock_enabled:
            provider_subject = f"mock-{provider_key}-{body.code[:12]}"
            profile_email = f"{provider_key}.{body.code[:12]}@sso.local"
            profile = {
                "provider_subject": provider_subject,
                "email": profile_email,
                "email_verified": True,
            }
        else:
            redirect_uri = body.redirect_uri or os.getenv(
                f"AUTH_SSO_{provider_key.upper()}_REDIRECT_URI",
                "",
            )
            if not redirect_uri:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "code": "INVALID_REQUEST",
                        "message": "redirect_uri is required for provider token exchange",
                    },
                )
            try:
                sso_profile = await sso_client.exchange_code_for_profile(
                    provider_key,
                    code=body.code,
                    state=body.state,
                    redirect_uri=redirect_uri,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": "SSO_EXCHANGE_FAILED", "message": str(exc)},
                ) from exc
            profile = {
                "provider_subject": sso_profile.provider_subject,
                "email": sso_profile.email if sso_profile.email_verified else None,
                "email_verified": sso_profile.email_verified,
            }

        if not profile["provider_subject"]:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": "SSO_PROFILE_INVALID", "message": "provider subject is missing"},
            )

        sso_result = await auth_store.login_with_sso(
            provider=provider_key,
            provider_subject=profile["provider_subject"],
            email=profile["email"],
            role="guardian",
        )
        await user_bootstrap.ensure_user(
            user_id=sso_result.user.user_id,
            email=sso_result.user.email,
            role=sso_result.user.role,
            auth_user_id=sso_result.user.user_id,
            auth_source=sso_result.user.auth_source,
            profile_data={},
        )
        return success_response(
            {
                "user_id": sso_result.user.user_id,
                "role": sso_result.user.role,
                "is_signup": sso_result.is_signup,
                "linked_existing_account": sso_result.linked_existing_account,
                **_issue_tokens(jwt, user_id=sso_result.user.user_id, role=sso_result.user.role),
            },
            meta={"provider": provider_key, "state": body.state},
        )

    return app


app = create_app()
