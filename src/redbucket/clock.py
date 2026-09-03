"""UTC ISO-8601 时间戳。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> str:
    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    return stamp.isoformat().replace("+00:00", "Z")


def utc_in(seconds: int) -> str:
    """A stamp `seconds` from now, same shape as utc_now()."""
    stamp = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_past(stamp: str) -> bool:
    moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    return moment < datetime.now(timezone.utc)
