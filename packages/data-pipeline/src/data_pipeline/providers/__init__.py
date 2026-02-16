"""Provider adapters."""

from data_pipeline.providers.factory import build_provider_adapter
from data_pipeline.providers.gyeonggi import GyeonggiAdapter
from data_pipeline.providers.mohw import MohwAdapter
from data_pipeline.providers.national import NationalAdapter
from data_pipeline.providers.seoul import SeoulAdapter
from data_pipeline.providers.seoul_district import SeoulDistrictAdapter

__all__ = [
    "SeoulAdapter",
    "SeoulDistrictAdapter",
    "GyeonggiAdapter",
    "NationalAdapter",
    "MohwAdapter",
    "build_provider_adapter",
]
