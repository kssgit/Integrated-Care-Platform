from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import API_EVENTS_TOPIC
from shared.events import build_event_envelope


async def publish_etl_completed_event(
    broker: MessageBroker,
    provider: str,
    saved_count: int,
) -> None:
    envelope = build_event_envelope(
        "etl_completed",
        {"provider": provider, "saved_count": saved_count},
    )
    payload = envelope.to_dict()
    payload["event_type"] = "etl_completed"
    payload["saved_count"] = saved_count
    message = EtlMessage(
        trace_id=str(uuid4()),
        provider=provider,
        payload=payload,
        timestamp=datetime.now(timezone.utc),
        retry_count=0,
    )
    await broker.publish(API_EVENTS_TOPIC, message)

