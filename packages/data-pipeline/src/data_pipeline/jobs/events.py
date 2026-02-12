from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import API_EVENTS_TOPIC


async def publish_etl_completed_event(
    broker: MessageBroker,
    provider: str,
    saved_count: int,
) -> None:
    message = EtlMessage(
        trace_id=str(uuid4()),
        provider=provider,
        payload={"event_type": "etl_completed", "saved_count": saved_count},
        timestamp=datetime.now(timezone.utc),
        retry_count=0,
    )
    await broker.publish(API_EVENTS_TOPIC, message)

