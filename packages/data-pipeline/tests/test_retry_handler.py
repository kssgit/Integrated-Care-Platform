from datetime import datetime, timezone

import pytest

from data_pipeline.messaging.broker import InMemoryMessageBroker
from data_pipeline.messaging.retry_handler import RetryHandler
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import ETL_ERRORS_TOPIC, ETL_RAW_EVENTS_TOPIC


def build_message(retry_count: int = 0) -> EtlMessage:
    return EtlMessage(
        trace_id="trace-1",
        provider="seoul_open_data",
        payload={"source_id": "x"},
        timestamp=datetime.now(timezone.utc),
        retry_count=retry_count,
    )


@pytest.mark.asyncio
async def test_retry_handler_requeues_before_max_retries() -> None:
    broker = InMemoryMessageBroker()
    handler = RetryHandler(broker=broker, max_retries=3, retry_delay_seconds=60)
    sleeps: list[int] = []

    async def fake_sleep(seconds: int) -> None:
        sleeps.append(seconds)

    published_topic = await handler.handle_failure(build_message(retry_count=1), fake_sleep)

    assert published_topic == ETL_RAW_EVENTS_TOPIC
    assert sleeps == [60]
    assert len(broker.published[ETL_RAW_EVENTS_TOPIC]) == 1
    assert broker.published[ETL_RAW_EVENTS_TOPIC][0].retry_count == 2


@pytest.mark.asyncio
async def test_retry_handler_sends_to_dlq_after_max_retries() -> None:
    broker = InMemoryMessageBroker()
    handler = RetryHandler(broker=broker, max_retries=3, retry_delay_seconds=60)

    async def fake_sleep(_: int) -> None:
        raise AssertionError("sleep should not be called for DLQ")

    published_topic = await handler.handle_failure(build_message(retry_count=3), fake_sleep)

    assert published_topic == ETL_ERRORS_TOPIC
    assert len(broker.published[ETL_ERRORS_TOPIC]) == 1
    assert broker.published[ETL_ERRORS_TOPIC][0].retry_count == 3

