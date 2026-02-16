from fastapi.testclient import TestClient

from facility_service.app import create_app


def test_list_and_detail() -> None:
    client = TestClient(create_app())
    listed = client.get("/v1/facilities?page=1&page_size=2")
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 2

    first_id = listed.json()["data"][0]["id"]
    detail = client.get(f"/v1/facilities/{first_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == first_id


def test_search_validation() -> None:
    client = TestClient(create_app())
    bad = client.get("/v1/facilities/search?query=';DROP")
    assert bad.status_code == 422

