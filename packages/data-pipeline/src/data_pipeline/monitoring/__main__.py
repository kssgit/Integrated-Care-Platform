from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("PIPELINE_MONITORING_HOST", "0.0.0.0")
    port = int(os.getenv("PIPELINE_MONITORING_PORT", "8001"))
    uvicorn.run("data_pipeline.monitoring.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

