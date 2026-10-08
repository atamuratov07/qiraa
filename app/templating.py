from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import StrictUndefined

from app.timeutils import local_day

APP_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=APP_DIR / "templates")

# With the default, a typo like {{ q.promt }} silently shows nothing.
templates.env.undefined = StrictUndefined


RU_MONTHS = (
    "янв",
    "фев",
    "мар",
    "апр",
    "мая",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)
RU_WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def ru_date(day: date, fmt: str = "%-d %b %Y") -> str:
    # strftime's %a/%b follow the server locale (English in Docker), so fill them in here.
    # %-d (day without a leading zero) is handled here too: Windows strftime doesn't know it.
    fmt = (
        fmt.replace("%-d", str(day.day))
        .replace("%b", RU_MONTHS[day.month - 1])
        .replace("%a", RU_WEEKDAYS[day.weekday()])
    )
    return day.strftime(fmt)


def local_date(moment: datetime, fmt: str = "%-d %b %Y") -> str:
    # Without it, templates would print the UTC date, a day early between 00:00 and 05:00.
    return ru_date(local_day(moment), fmt)


def plural(n: int, one: str, few: str, many: str) -> str:
    """Russian plural form for n: 1 вопрос, 2 вопроса, 5 вопросов, 21 вопрос, 11 вопросов."""
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    if n % 10 == 1:
        return one
    if 2 <= n % 10 <= 4:
        return few
    return many


templates.env.filters["local_date"] = local_date
templates.env.filters["ru_date"] = ru_date
templates.env.filters["plural"] = plural


def render(
    request: Request,
    name: str,
    context: Mapping[str, object],
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, name, dict(context), status_code=status_code
    )
