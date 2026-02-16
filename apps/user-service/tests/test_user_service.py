from uuid import uuid4

from fastapi.testclient import TestClient

from shared.security import JWTManager
from user_service.app import create_app


def _token(role: str, subject: str | None = None) -> str:
    jwt = JWTManager(secret="dev-only-secret")
    return jwt.issue_access_token(subject or str(uuid4()), role, jti=str(uuid4()))


def test_admin_can_create_user() -> None:
    client = TestClient(create_app())
    token = _token("admin")
    response = client.post(
        "/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "user@example.com", "role": "guardian", "phone": "010-1111-2222"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "user@example.com"
    assert body["phone_encrypted"] is not None
    assert body["phone_hash"] is not None


def test_non_admin_cannot_create_user() -> None:
    client = TestClient(create_app())
    token = _token("guardian")
    response = client.post(
        "/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "user@example.com", "role": "guardian"},
    )
    assert response.status_code == 403


def test_invalid_token_is_rejected() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/users",
        headers={"Authorization": "Bearer not-a-token"},
        json={"email": "user@example.com", "role": "guardian"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
