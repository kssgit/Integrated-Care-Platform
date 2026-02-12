from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from data_pipeline.core.models import ProviderEvent


class BaseProviderAdapter(ABC):
    provider_name: str

    @abstractmethod
    async def fetch_raw_events(self) -> list[ProviderEvent]:
        raise NotImplementedError

    def build_event(self, trace_id: str, payload: dict) -> ProviderEvent:
        return ProviderEvent(
            trace_id=trace_id,
            provider=self.provider_name,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
        )
