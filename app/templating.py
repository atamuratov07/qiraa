from collections.abc import Mapping
from datetime import datetime
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


def local_date(moment: datetime, fmt: str = "%d %b %Y") -> str:
    # Without it, templates would print the UTC date, a day early between 00:00 and 05:00.
    return local_day(moment).strftime(fmt)


templates.env.filters["local_date"] = local_date


def render(
    request: Request,
    name: str,
    context: Mapping[str, object],
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, name, dict(context), status_code=status_code
    )
