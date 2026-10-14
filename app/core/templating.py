from collections.abc import Mapping
from datetime import date, datetime

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import StrictUndefined

from app.core.config import APP_DIR
from app.core.i18n import translations
from app.core.timeutils import local_day

templates = Jinja2Templates(directory=APP_DIR / "templates")

templates.env.undefined = StrictUndefined


def _jinja_gettext(message: str) -> str:
    return translations().gettext(message)


def _jinja_ngettext(singular: str, plural: str, n: int) -> str:
    return translations().ngettext(singular, plural, n)


# _() and {% trans %} look up the current request's language on every call. Installed
# once, before any template compiles: Jinja fixes "newstyle" gettext at compile time.
# Newstyle fills in %(name)s placeholders and escapes the values, so it gets the raw
# catalog lookups.
templates.env.add_extension("jinja2.ext.i18n")
templates.env.policies["ext.i18n.trimmed"] = True
templates.env.install_gettext_callables(  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
    gettext=_jinja_gettext, ngettext=_jinja_ngettext, newstyle=True
)


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
    return ru_date(local_day(moment), fmt)


def plural(n: int, one: str, few: str, many: str) -> str:
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
