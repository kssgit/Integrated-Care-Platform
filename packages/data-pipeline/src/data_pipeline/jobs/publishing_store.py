from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.pipeline import FacilityStore
from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import ETL_NORMALIZED_TOPIC, FACILITY_EVENTS_TOPIC
from shared.events import build_event_envelope


class PublishingFacilityStore(FacilityStore):
    def __init__(
        self,
        delegate: FacilityStore,
        broker: MessageBroker,
        provider: str,
    ) -> None:
        self._delegate = delegate
        self._broker = broker
        self._provider = provider

    async def upsert_many(self, records: list[FacilityRecord]) -> int:
        saved_count = await self._delegate.upsert_many(records)
        for record in records:
            normalized_message, facility_event_message = self._build_messages(record)
            await self._broker.publish(ETL_NORMALIZED_TOPIC, normalized_message)
            await self._broker.publish(FACILITY_EVENTS_TOPIC, facility_event_message)
        return saved_count

    def _build_messages(self, record: FacilityRecord) -> tuple[EtlMessage, EtlMessage]:
        payload = {
            "source_id": record.source_id,
            "name": record.name,
            "address": record.address,
            "district_code": record.district_code,
            "lat": record.lat,
            "lng": record.lng,
            "source_updated_at": record.source_updated_at.isoformat(),
        }
        normalized = EtlMessage(
            trace_id=str(uuid4()),
            provider=self._provider,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            retry_count=0,
        )
        envelope = build_event_envelope("facility.updated", payload)
        facility_event = EtlMessage(
            trace_id=envelope.trace_id,
            provider=self._provider,
            payload=envelope.to_dict(),
            timestamp=datetime.now(timezone.utc),
            retry_count=0,
        )
        return normalized, facility_event

