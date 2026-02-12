from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from data_pipeline.core.models import ProviderEvent
from data_pipeline.core.retry import with_exponential_backoff
from data_pipeline.providers.base import BaseProviderAdapter

logger = logging.getLogger(__name__)


class SeoulAdapter(BaseProviderAdapter):
    provider_name = "seoul_open_data"

    def __init__(
        self,
        fetch_page: Callable[[int], Awaitable[list[dict[str, Any]]]],
        start_page: int = 1,
        end_page: int = 1,
        max_concurrency: int = 5,
    ) -> None:
        self._fetch_page = fetch_page
        self._start_page = start_page
        self._end_page = end_page
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_raw_events(self) -> list[ProviderEvent]:
        logger.info(
            "provider_fetch_started",
            extra={"provider": self.provider_name, "start_page": self._start_page, "end_page": self._end_page},
        )
        pages = range(self._start_page, self._end_page + 1)
        tasks = [self._fetch_page_with_limit(page) for page in pages]
        results = await asyncio.gather(*tasks)
        events = [self.build_event(str(uuid.uuid4()), item) for batch in results for item in batch]
        logger.info(
            "provider_fetch_completed",
            extra={"provider": self.provider_name, "event_count": len(events)},
        )
        return events

    async def _fetch_page_with_limit(self, page: int) -> list[dict[str, Any]]:
        async with self._semaphore:
            return await with_exponential_backoff(
                lambda: self._fetch_page(page),
                retries=3,
                base_delay_seconds=0.05,
            )
