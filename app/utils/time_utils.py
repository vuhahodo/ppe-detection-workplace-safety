from __future__ import annotations

from datetime import datetime


def now_local() -> datetime:
    return datetime.now()


def timestamp_str() -> str:
    return now_local().strftime("%Y-%m-%d %H:%M:%S")


def date_str() -> str:
    return now_local().strftime("%Y-%m-%d")
