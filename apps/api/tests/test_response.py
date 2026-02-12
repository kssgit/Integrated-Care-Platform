from api.response import error_response, success_response


def test_success_response_shape() -> None:
    payload = success_response({"id": 1}, {"page": 1})
    assert payload["success"] is True
    assert payload["data"] == {"id": 1}
    assert payload["meta"] == {"page": 1}


def test_error_response_shape() -> None:
    payload = error_response("NOT_FOUND", "missing")
    assert payload["success"] is False
    assert payload["error"]["code"] == "NOT_FOUND"
    assert payload["error"]["message"] == "missing"

