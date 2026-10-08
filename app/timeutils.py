from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def as_utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def local_day(moment: datetime) -> date:
    return as_utc(moment).astimezone(ZoneInfo(get_settings().app_timezone)).date()
