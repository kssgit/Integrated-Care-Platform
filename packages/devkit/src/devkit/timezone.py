from __future__ import annotations

from datetime import datetime
import os
import time
from zoneinfo import ZoneInfo

KST_ZONE = ZoneInfo("Asia/Seoul")

_configured = False


def configure_kst_timezone() -> None:
    global _configured
    if _configured:
        return
    os.environ["TZ"] = "Asia/Seoul"
    if hasattr(time, "tzset"):
        time.tzset()
    _configured = True


def now_kst() -> datetime:
    return datetime.now(KST_ZONE)


def now_kst_iso() -> str:
    return now_kst().isoformat()
