from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class EventEnvelope:
    event_version: str
    event_type: str
    trace_id: str
    occurred_at: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_version": self.event_version,
            "event_type": self.event_type,
            "trace_id": self.trace_id,
            "occurred_at": self.occurred_at,
            "payload": self.payload,
        }


def build_event_envelope(event_type: str, payload: dict[str, Any], *, trace_id: str | None = None) -> EventEnvelope:
    return EventEnvelope(
        event_version="v1",
        event_type=event_type,
        trace_id=trace_id or str(uuid4()),
        occurred_at=datetime.now(timezone.utc).isoformat(),
        payload=payload,
    )

