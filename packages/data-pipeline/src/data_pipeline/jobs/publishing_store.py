from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from data_pipeline.core.models import FacilityRecord
from data_pipeline.core.pipeline import FacilityStore
from data_pipeline.messaging.broker import MessageBroker
from data_pipeline.messaging.schema import EtlMessage
from data_pipeline.messaging.topics import ETL_NORMALIZED_TOPIC


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
            message = self._build_message(record)
            await self._broker.publish(ETL_NORMALIZED_TOPIC, message)
        return saved_count

    def _build_message(self, record: FacilityRecord) -> EtlMessage:
        payload = {
            "source_id": record.source_id,
            "name": record.name,
            "address": record.address,
            "district_code": record.district_code,
            "lat": record.lat,
            "lng": record.lng,
            "source_updated_at": record.source_updated_at.isoformat(),
        }
        return EtlMessage(
            trace_id=str(uuid4()),
            provider=self._provider,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            retry_count=0,
        )

