import pytest

from data_pipeline.jobs.events import publish_etl_completed_event
from data_pipeline.messaging.broker import InMemoryMessageBroker
from data_pipeline.messaging.topics import API_EVENTS_TOPIC


@pytest.mark.asyncio
async def test_publish_etl_completed_event() -> None:
    broker = InMemoryMessageBroker()
    await publish_etl_completed_event(
        broker=broker,
        provider="seoul_open_data",
        saved_count=42,
    )

    assert len(broker.published[API_EVENTS_TOPIC]) == 1
    payload = broker.published[API_EVENTS_TOPIC][0].payload
    assert payload["event_type"] == "etl_completed"
    assert payload["saved_count"] == 42

