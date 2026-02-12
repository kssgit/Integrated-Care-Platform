from __future__ import annotations

import pytest

from data_pipeline.providers.factory import build_provider_adapter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_name", "expected_provider"),
    [
        ("seoul_open_data", "seoul_open_data"),
        ("gyeonggi_open_data", "gyeonggi_open_data"),
        ("national_open_data", "national_open_data"),
    ],
)
async def test_provider_factory_builds_supported_adapters(
    provider_name: str,
    expected_provider: str,
) -> None:
    async def fetch_page(page: int) -> list[dict]:
        return [{"source_id": f"id-{page}"}]

    adapter = build_provider_adapter(
        provider_name=provider_name,
        fetch_page=fetch_page,
        start_page=1,
        end_page=1,
    )
    events = await adapter.fetch_raw_events()

    assert adapter.provider_name == expected_provider
    assert len(events) == 1
    assert events[0].provider == expected_provider


def test_provider_factory_raises_for_unsupported_provider() -> None:
    async def fetch_page(_: int) -> list[dict]:
        return []

    with pytest.raises(ValueError):
        build_provider_adapter(
            provider_name="invalid_provider",
            fetch_page=fetch_page,
            start_page=1,
            end_page=1,
        )
