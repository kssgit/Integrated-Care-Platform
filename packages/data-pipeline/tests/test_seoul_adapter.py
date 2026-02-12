import asyncio

import pytest

from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.providers.seoul import SeoulAdapter


@pytest.mark.asyncio
async def test_seoul_adapter_collects_events_from_multiple_pages() -> None:
    async def fetch_page(page: int) -> list[dict]:
        await asyncio.sleep(0)
        return [{"source_id": f"id-{page}"}]

    adapter = SeoulAdapter(fetch_page=fetch_page, start_page=1, end_page=3, max_concurrency=2)
    events = await adapter.fetch_raw_events()

    assert len(events) == 3
    assert {event.payload["source_id"] for event in events} == {"id-1", "id-2", "id-3"}


@pytest.mark.asyncio
async def test_seoul_adapter_counts_external_errors_on_retry() -> None:
    state = {"called": 0}
    metrics = InMemoryPipelineMetricsCollector()

    async def flaky_fetch_page(_: int) -> list[dict]:
        state["called"] += 1
        if state["called"] < 3:
            raise RuntimeError("temporary provider failure")
        return [{"source_id": "id-1"}]

    adapter = SeoulAdapter(
        fetch_page=flaky_fetch_page,
        start_page=1,
        end_page=1,
        max_concurrency=1,
        metrics=metrics,
    )
    events = await adapter.fetch_raw_events()

    assert len(events) == 1
    assert metrics.external_api_error_count == 2
