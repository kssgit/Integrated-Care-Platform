from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("ADMIN_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("ADMIN_SERVICE_PORT", "8105"))
    uvicorn.run("admin_service.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
