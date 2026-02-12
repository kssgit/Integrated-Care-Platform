from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class EtlMessage:
    trace_id: str
    provider: str
    payload: dict[str, Any]
    timestamp: datetime
    retry_count: int = 0

