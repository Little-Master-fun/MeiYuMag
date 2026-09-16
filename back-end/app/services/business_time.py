"""Business dates are Beijing time; legacy SQLite naive values are local time."""
from datetime import datetime
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Shanghai")


def local_time(value: datetime) -> datetime:
    return value.replace(tzinfo=BUSINESS_TZ) if value.tzinfo is None else value.astimezone(BUSINESS_TZ)
