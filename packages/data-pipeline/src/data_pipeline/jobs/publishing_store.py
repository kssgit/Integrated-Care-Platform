from __future__ import annotations

from datetime import datetime, timezone
import logging
from uuid import uuid4

from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.pipeline import FacilityStore
from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import ETL_NORMALIZED_TOPIC, FACILITY_EVENTS_TOPIC
from shared.events import build_event_envelope

logger = logging.getLogger(__name__)


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
        publish_failures = 0
        for record in records:
            normalized_message, facility_event_message = self._build_messages(record)
            try:
                await self._broker.publish(ETL_NORMALIZED_TOPIC, normalized_message)
                await self._broker.publish(FACILITY_EVENTS_TOPIC, facility_event_message)
            except Exception:
                publish_failures += 1
                logger.exception(
                    "pipeline_publish_failed",
                    extra={"provider": self._provider, "source_id": record.source_id},
                )
        if publish_failures > 0:
            raise RuntimeError(
                f"publish failed after successful save: saved_count={saved_count}, publish_failures={publish_failures}"
            )
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
