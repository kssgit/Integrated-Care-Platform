from fastapi.testclient import TestClient

from api.app import create_app


def test_trace_header_is_propagated() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz", headers={"x-trace-id": "trace-abc"})

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "trace-abc"


def test_api_latency_metric_is_collected() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/healthz")
    metrics = app.state.api_metrics.snapshot()

    assert response.status_code == 200
    assert len(metrics) >= 1
    assert metrics[-1]["path"] == "/healthz"
    assert metrics[-1]["status_code"] == 200
    assert metrics[-1]["duration_ms"] >= 0

