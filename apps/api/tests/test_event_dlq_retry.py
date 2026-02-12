import json

from api.event_dlq_retry import ApiEventDlqRetryWorker, DlqRetryConfig


def test_dlq_retry_republishes_to_target_topic() -> None:
    worker = ApiEventDlqRetryWorker(config=DlqRetryConfig(max_attempts=3))
    dlq_payload = {
        "error": "x",
        "raw_value": json.dumps({"trace_id": "t1", "payload": {"event_type": "etl_completed"}}),
    }
    topic, payload = worker._handle_dlq_value(
        json.dumps(dlq_payload).encode("utf-8"),
        target_topic="api-events",
        parking_topic="api-events-parking",
    )
    republished = json.loads(payload.decode("utf-8"))

    assert topic == "api-events"
    assert republished["trace_id"] == "t1"
    assert republished["dlq_retry_count"] == 1


def test_dlq_retry_sends_to_parking_after_max_attempts() -> None:
    worker = ApiEventDlqRetryWorker(config=DlqRetryConfig(max_attempts=2))
    dlq_payload = {
        "error": "x",
        "raw_value": json.dumps(
            {"trace_id": "t1", "payload": {"event_type": "etl_completed"}, "dlq_retry_count": 2}
        ),
    }
    raw = json.dumps(dlq_payload).encode("utf-8")
    topic, payload = worker._handle_dlq_value(
        raw,
        target_topic="api-events",
        parking_topic="api-events-parking",
    )

    assert topic == "api-events-parking"
    assert payload == raw


def test_dlq_retry_sends_invalid_payload_to_parking() -> None:
    worker = ApiEventDlqRetryWorker(config=DlqRetryConfig(max_attempts=2))
    raw = b"invalid-json"
    topic, payload = worker._handle_dlq_value(
        raw,
        target_topic="api-events",
        parking_topic="api-events-parking",
    )

    assert topic == "api-events-parking"
    assert payload == raw

