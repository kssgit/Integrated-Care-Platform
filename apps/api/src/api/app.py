from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response

from api.errors import ApiError
from api.middleware import ObservabilityMiddleware
from api.observability import (
    CompositeApiMetricsCollector,
    InMemoryApiMetricsCollector,
    PrometheusApiMetricsCollector,
)
from api.response import error_response, success_response
from api.routers.facilities import router as facilities_router
from api.routers.geo import router as geo_router
from api.routers.internal_events import router as internal_events_router
from api.routers.auth_gateway import router as auth_gateway_router
from api.routers.search_gateway import router as search_gateway_router
from api.routers.trust_safety import router as trust_safety_router
from api.routers.users_gateway import router as users_gateway_router
from api.telemetry import configure_otel, configure_probe_access_log_filter


def create_app() -> FastAPI:
    app = FastAPI(title="Integrated Care API", version="0.1.0")
    configure_otel(service_name="integrated-care-api")
    configure_probe_access_log_filter()
    app.state.api_metrics = InMemoryApiMetricsCollector()
    app.state.prom_metrics = PrometheusApiMetricsCollector()
    app.state.composite_metrics = CompositeApiMetricsCollector(
        [app.state.api_metrics, app.state.prom_metrics]
    )
    app.add_middleware(ObservabilityMiddleware, collector=app.state.composite_metrics)
    app.include_router(auth_gateway_router)
    app.include_router(users_gateway_router)
    app.include_router(facilities_router)
    app.include_router(search_gateway_router)
    app.include_router(geo_router)
    app.include_router(internal_events_router)
    app.include_router(trust_safety_router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return success_response({"status": "ok"}, meta={})

    @app.get("/readyz")
    async def readyz() -> dict:
        return success_response({"status": "ready"}, meta={})

    @app.get("/metrics")
    async def metrics() -> Response:
        payload = app.state.prom_metrics.render()
        return Response(content=payload, media_type="text/plain; version=0.0.4")

    @app.get("/dev/api-test", response_class=HTMLResponse)
    async def api_test_page() -> str:
        return """
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Integrated Care API Test</title>
    <style>
      body { font-family: sans-serif; max-width: 900px; margin: 24px auto; padding: 0 12px; }
      input, button, textarea { width: 100%; margin-top: 8px; padding: 8px; box-sizing: border-box; }
      button { cursor: pointer; }
      .row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .muted { color: #666; font-size: 13px; }
      pre { background: #111; color: #eaeaea; padding: 12px; border-radius: 8px; overflow: auto; }
      h3 { margin-top: 20px; }
    </style>
  </head>
  <body>
    <h1>Integrated Care API Quick Test</h1>
    <p class="muted">Swagger: <a href="/docs" target="_blank">/docs</a></p>

    <h3>Auth</h3>
    <label>Email</label>
    <input id="email" value="test@example.com" />
    <label>Password</label>
    <input id="password" value="password123" />
    <div class="row">
      <button onclick="signup()">Signup</button>
      <button onclick="login()">Login</button>
      <button onclick="me()">Me</button>
    </div>
    <button onclick="refreshToken()">Refresh</button>
    <div class="row">
      <button onclick="ssoAuthorize('google')">Google SSO Authorize</button>
      <button onclick="ssoAuthorize('naver')">Naver SSO Authorize</button>
    </div>

    <label>Access Token</label>
    <textarea id="access" rows="3"></textarea>
    <label>Refresh Token</label>
    <textarea id="refresh" rows="3"></textarea>

    <h3>Facilities</h3>
    <button onclick="listFacilities()">GET /v1/facilities</button>

    <h3>Users</h3>
    <label>User Email</label>
    <input id="userEmail" value="new.user@example.com" />
    <button onclick="createUser()">POST /v1/users</button>
    <label>Last Created User ID</label>
    <input id="userId" />
    <button onclick="getUser()">GET /v1/users/{user_id}</button>

    <h3>Response</h3>
    <pre id="out">ready</pre>

    <script>
      async function req(path, method, body=null, auth=true) {
        const headers = { "Content-Type": "application/json" };
        if (auth) {
          const token = document.getElementById("access").value.trim();
          if (token) headers["Authorization"] = "Bearer " + token;
        }
        const res = await fetch(path, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
        });
        const text = await res.text();
        document.getElementById("out").textContent = `HTTP ${res.status}\\n${text}`;
        try { return JSON.parse(text); } catch { return null; }
      }

      async function login() {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const data = await req("/v1/auth/login", "POST", { email, password, role: "guardian" }, false);
        if (data && data.success) {
          document.getElementById("access").value = data.data.access_token || "";
          document.getElementById("refresh").value = data.data.refresh_token || "";
        }
      }
      async function signup() {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;
        const data = await req("/v1/auth/signup", "POST", { email, password, role: "guardian" }, false);
        if (data && data.success) {
          document.getElementById("access").value = data.data.access_token || "";
          document.getElementById("refresh").value = data.data.refresh_token || "";
        }
      }

      async function me() { await req("/v1/auth/me", "GET"); }
      async function refreshToken() {
        const refreshToken = document.getElementById("refresh").value.trim();
        const data = await req("/v1/auth/refresh", "POST", { refresh_token: refreshToken }, false);
        if (data && data.success) {
          document.getElementById("access").value = data.data.access_token || "";
        }
      }
      async function ssoAuthorize(provider) {
        const redirectUri = window.location.origin + "/dev/api-test";
        await req(`/v1/auth/sso/${provider}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`, "GET", null, false);
      }
      async function listFacilities() { await req("/v1/facilities?page=1&page_size=5", "GET"); }

      async function createUser() {
        const email = document.getElementById("userEmail").value.trim();
        const body = {
          email,
          phone: "01012345678",
          role: "guardian",
          profile_data: { name: "quick-test-user" }
        };
        const data = await req("/v1/users", "POST", body);
        if (data && data.success && data.data && data.data.user_id) {
          document.getElementById("userId").value = data.data.user_id;
        }
      }

      async function getUser() {
        const userId = document.getElementById("userId").value.trim();
        if (!userId) {
          document.getElementById("out").textContent = "userId is empty";
          return;
        }
        await req(`/v1/users/${userId}`, "GET");
      }
    </script>
  </body>
</html>
        """

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        message = "; ".join(err["msg"] for err in exc.errors())
        return JSONResponse(
            status_code=422,
            content=error_response("VALIDATION_ERROR", message),
        )

    return app


app = create_app()
