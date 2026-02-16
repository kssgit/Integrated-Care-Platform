import pytest
from fastapi.testclient import TestClient

from auth_service.app import create_app
from auth_service.sso import SSOProfile


def test_login_refresh_me_flow() -> None:
    client = TestClient(create_app())

    login = client.post(
        "/v1/auth/login",
        json={"email": "test@example.com", "password": "password123", "role": "guardian"},
    )
    assert login.status_code == 200
    tokens = login.json()["data"]
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "guardian"

    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()["data"]


def test_logout_revokes_refresh() -> None:
    client = TestClient(create_app())
    login = client.post(
        "/v1/auth/login",
        json={"email": "test@example.com", "password": "password123", "role": "guardian"},
    )
    refresh = login.json()["data"]["refresh_token"]

    logout = client.post("/v1/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 200

    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": refresh})
    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "TOKEN_REVOKED"


def test_login_rejects_invalid_credentials() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/auth/login",
        json={"email": "test@example.com", "password": "wrong-password", "role": "admin"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_does_not_trust_role_from_request() -> None:
    client = TestClient(create_app())
    login = client.post(
        "/v1/auth/login",
        json={"email": "test@example.com", "password": "password123", "role": "admin"},
    )
    access = login.json()["data"]["access_token"]
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "guardian"


def test_dev_auth_test_page_exists() -> None:
    client = TestClient(create_app())
    response = client.get("/dev/auth-test")
    assert response.status_code == 200
    assert "Auth Service Test" in response.text


def test_signup_creates_user_and_returns_tokens() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/auth/signup",
        json={"email": "signup.user@example.com", "password": "password123", "role": "guardian"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["user_id"] == "signup.user@example.com"
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]


def test_signup_duplicate_email_returns_409() -> None:
    client = TestClient(create_app())
    first = client.post(
        "/v1/auth/signup",
        json={"email": "dup.user@example.com", "password": "password123", "role": "guardian"},
    )
    second = client.post(
        "/v1/auth/signup",
        json={"email": "dup.user@example.com", "password": "password123", "role": "guardian"},
    )
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "USER_ALREADY_EXISTS"


def test_sso_authorize_without_config_returns_not_configured() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/auth/sso/google/authorize?redirect_uri=http://localhost/callback")
    assert response.status_code == 200
    assert response.json()["data"]["configured"] is False


def test_sso_callback_links_existing_local_account(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_exchange(self, provider: str, *, code: str, state: str, redirect_uri: str):
        return SSOProfile(
            provider=provider,
            provider_subject="google-subject-001",
            email="link.user@example.com",
            email_verified=True,
            name="Link User",
        )

    monkeypatch.setattr("auth_service.sso.SSOClient.exchange_code_for_profile", _fake_exchange)

    client = TestClient(create_app())
    signup = client.post(
        "/v1/auth/signup",
        json={"email": "link.user@example.com", "password": "password123", "role": "guardian"},
    )
    assert signup.status_code == 200

    callback = client.post(
        "/v1/auth/sso/google/callback",
        json={
            "code": "oauth-code",
            "state": "opaque-state",
            "redirect_uri": "http://localhost/callback",
        },
    )
    assert callback.status_code == 200
    data = callback.json()["data"]
    assert data["user_id"] == "link.user@example.com"
    assert data["linked_existing_account"] is True
    assert data["is_signup"] is False
