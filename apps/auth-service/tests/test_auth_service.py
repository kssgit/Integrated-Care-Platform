from fastapi.testclient import TestClient

from auth_service.app import create_app


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
