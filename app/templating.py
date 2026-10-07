from collections.abc import Mapping
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import StrictUndefined

APP_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=APP_DIR / "templates")

# With the default, a typo like {{ q.promt }} silently shows nothing.
templates.env.undefined = StrictUndefined


def render(
    request: Request,
    name: str,
    context: Mapping[str, object],
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, name, dict(context), status_code=status_code
    )
