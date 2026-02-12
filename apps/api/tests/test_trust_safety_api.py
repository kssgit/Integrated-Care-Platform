from fastapi.testclient import TestClient

from api.app import create_app


def test_safe_number_route_response_shape() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/trust-safety/safe-number/route",
        json={
            "caller_phone": "010-1234-5678",
            "callee_phone": "010-1111-2222",
            "ttl_minutes": 30,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["relay_number"].startswith("050-")
    assert body["data"]["masked_caller"] == "010****678"
    assert body["data"]["masked_callee"] == "010****222"


def test_safe_number_route_validation_error() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/trust-safety/safe-number/route",
        json={
            "caller_phone": "010-1234-5678",
            "callee_phone": "010-1111-2222",
            "ttl_minutes": 0,
        },
    )
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"

