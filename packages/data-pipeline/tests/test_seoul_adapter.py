import asyncio

import pytest

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

