from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Optional

KST = timezone(timedelta(hours=9))


def format_kst_time(dt: Optional[datetime]) -> str:
    if dt is None:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
