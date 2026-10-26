from collections.abc import Mapping
from datetime import date, datetime

from babel.dates import format_skeleton
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jinja2 import StrictUndefined

from app.core.config import APP_DIR
from app.core.i18n import LANGUAGES, current_locale, translations
from app.core.redirects import return_path
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
# tojson keeps <, >, & and ' escaped either way; this only leaves letters readable.
templates.env.policies["json.dumps_kwargs"] = {"ensure_ascii": False, "sort_keys": True}
templates.env.install_gettext_callables(  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
    gettext=_jinja_gettext, ngettext=_jinja_ngettext, newstyle=True
)


def local_date(value: date, skeleton: str = "yMMMd") -> str:
    day = local_day(value) if isinstance(value, datetime) else value
    return format_skeleton(skeleton, day, locale=current_locale())


templates.env.filters["local_date"] = local_date


def render(
    request: Request,
    name: str,
    context: Mapping[str, object],
    status_code: int = 200,
) -> HTMLResponse:
    page = {
        **context,
        "current_locale": current_locale(),
        "languages": LANGUAGES,
        "return_path": return_path(request),
    }
    return templates.TemplateResponse(request, name, page, status_code=status_code)
