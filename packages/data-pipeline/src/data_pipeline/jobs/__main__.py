from __future__ import annotations

import asyncio
import os

from data_pipeline.jobs.daily_sync import run_daily_sync
from data_pipeline.jobs.extractor import ProviderFacilityExtractor
from data_pipeline.jobs.store import JsonlFacilityStore


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def main() -> None:
    base_url = _required_env("FACILITY_PROVIDER_BASE_URL")
    output_path = os.getenv("PIPELINE_OUTPUT_FILE", "runtime/facilities.jsonl")
    page_size = int(os.getenv("PIPELINE_PAGE_SIZE", "200"))
    start_page = int(os.getenv("PIPELINE_START_PAGE", "1"))
    end_page = int(os.getenv("PIPELINE_END_PAGE", "1"))

    extractor = ProviderFacilityExtractor(
        base_url=base_url,
        page_size=page_size,
        start_page=start_page,
        end_page=end_page,
    )
    store = JsonlFacilityStore(file_path=output_path)
    asyncio.run(run_daily_sync(extractor=extractor, store=store))


if __name__ == "__main__":
    main()

