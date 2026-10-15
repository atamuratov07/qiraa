"""
`_` is the translation function in Python and templates, never a throwaway name: a
function that binds `_` (`x, _, y = ...`) can't call `_()` anymore.
"""

import io
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from babel import negotiate_locale
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po
from babel.support import NullTranslations, Translations
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import APP_DIR, get_settings

LANGUAGES = {"uz": "Oʻzbekcha", "ru": "Русский", "en": "English"}
LOCALES = tuple(LANGUAGES)
DEFAULT_LOCALE = "en"
LOCALE_COOKIE = "qiraa_lang"
LOCALE_DIR = APP_DIR / "locale"


def load_catalog(path: Path) -> NullTranslations:
    """Reads a .po file directly, so there are no compiled .mo files to keep in sync."""
    if not path.exists():
        return NullTranslations()

    with path.open("rb") as po:
        catalog = read_po(po)
    mo = io.BytesIO()
    write_mo(mo, catalog)
    mo.seek(0)

    return Translations(mo)


catalogs: dict[str, NullTranslations] = {
    code: load_catalog(LOCALE_DIR / code / "LC_MESSAGES" / "messages.po")
    for code in LOCALES
}
_current: ContextVar[str] = ContextVar("locale", default=DEFAULT_LOCALE)


def current_locale() -> str:
    return _current.get()


@contextmanager
def use_locale(code: str) -> Generator[None]:
    token = _current.set(code)
    try:
        yield
    finally:
        _current.reset(token)


def translations() -> NullTranslations:
    """Its methods don't fill in placeholders."""
    return catalogs[_current.get()]


def _(message: str, **params: object) -> str:
    text = translations().gettext(message)
    return text % params if params else text


def ngettext(singular: str, plural: str, n: int, **params: object) -> str:
    """`%(num)d` in the messages is the count, as in Jinja's `{% trans count=... %}`."""
    params.setdefault("num", n)
    return translations().ngettext(singular, plural, n) % params


def N_(message: str) -> str:
    """Marks a message for extraction only: at import time there is no request yet."""
    return message


def pick_locale(cookie: str | None, accept_language: str | None) -> str:
    if cookie in LOCALES:
        return cookie
    preferred = _accept_language(accept_language)
    return negotiate_locale(preferred, LOCALES, sep="-") or DEFAULT_LOCALE


def _accept_language(header: str | None) -> list[str]:
    ranked: list[tuple[float, str]] = []
    for part in (header or "").split(","):
        tag, *params = (piece.strip() for piece in part.split(";"))
        weight = 1.0
        for param in params:
            name, _sep, value = param.partition("=")
            if name == "q":
                try:
                    weight = float(value)
                except ValueError:
                    weight = 0.0
        if tag and tag != "*" and weight > 0:
            ranked.append((weight, tag))

    return [tag for _weight, tag in sorted(ranked, key=lambda item: -item[0])]


def set_locale_cookie(response: Response, code: str) -> None:
    settings = get_settings()
    response.set_cookie(
        LOCALE_COOKIE,
        code,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )


class LocaleMiddleware:
    """Pure ASGI, so the ContextVar is set in the request's own task; FastAPI copies
    it into the worker thread of a sync route. A global would mix up requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        code = pick_locale(
            request.cookies.get(LOCALE_COOKIE), request.headers.get("accept-language")
        )
        with use_locale(code):
            await self.app(scope, receive, send)
