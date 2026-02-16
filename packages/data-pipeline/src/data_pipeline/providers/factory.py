from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from data_pipeline.core.metrics import InMemoryPipelineMetricsCollector
from data_pipeline.providers.base import BaseProviderAdapter
from data_pipeline.providers.gyeonggi import GyeonggiAdapter
from data_pipeline.providers.mohw import MohwAdapter
from data_pipeline.providers.national import NationalAdapter
from data_pipeline.providers.seoul import SeoulAdapter
from data_pipeline.providers.seoul_district import SeoulDistrictAdapter

AdapterType = type[BaseProviderAdapter]

_ADAPTERS: dict[str, AdapterType] = {
    "seoul_open_data": SeoulAdapter,
    "seoul_district_open_data": SeoulDistrictAdapter,
    "gyeonggi_open_data": GyeonggiAdapter,
    "national_open_data": NationalAdapter,
    "mohw_open_data": MohwAdapter,
}


def build_provider_adapter(
    provider_name: str,
    fetch_page: Callable[[int], Awaitable[list[dict[str, Any]]]],
    start_page: int,
    end_page: int,
    max_concurrency: int = 5,
    metrics: InMemoryPipelineMetricsCollector | None = None,
) -> BaseProviderAdapter:
    adapter_type = _ADAPTERS.get(provider_name)
    if adapter_type is None:
        supported = ", ".join(sorted(_ADAPTERS.keys()))
        raise ValueError(f"unsupported provider '{provider_name}', supported: {supported}")
    return adapter_type(
        fetch_page=fetch_page,
        start_page=start_page,
        end_page=end_page,
        max_concurrency=max_concurrency,
        metrics=metrics,
    )
