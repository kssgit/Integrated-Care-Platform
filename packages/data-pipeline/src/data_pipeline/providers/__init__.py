"""Provider adapters."""

from data_pipeline.providers.factory import build_provider_adapter
from data_pipeline.providers.gyeonggi import GyeonggiAdapter
from data_pipeline.providers.national import NationalAdapter
from data_pipeline.providers.seoul import SeoulAdapter

__all__ = [
    "SeoulAdapter",
    "GyeonggiAdapter",
    "NationalAdapter",
    "build_provider_adapter",
]
