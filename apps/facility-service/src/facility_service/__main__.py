from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("FACILITY_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("FACILITY_SERVICE_PORT", "8103"))
    uvicorn.run("facility_service.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

