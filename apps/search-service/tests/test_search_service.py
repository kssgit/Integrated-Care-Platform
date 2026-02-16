from fastapi.testclient import TestClient

from search_service.app import create_app


def test_search_returns_results() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/search/facilities?query=gangnam")
    assert response.status_code == 200
    assert response.json()["meta"]["count"] >= 1


def test_search_blocks_invalid_query() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/search/facilities?query=';DROP")
    assert response.status_code == 422

