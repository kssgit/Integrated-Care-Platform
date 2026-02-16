from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class SlidingWindowLimiter:
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now_seconds: float) -> bool:
        bucket = self._windows[key]
        cutoff = now_seconds - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now_seconds)
        return True

