import asyncio
import time
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.core import i18n
from app.core.i18n import (
    LocaleMiddleware,
    _,
    current_locale,
    load_catalog,
    ngettext,
    pick_locale,
    use_locale,
)
from app.core.templating import templates

RU_PO = r"""
msgid ""
msgstr ""
"Language: ru\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && "
"n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\n"

msgid "Hello, %(name)s!"
msgstr "Привет, %(name)s!"

msgid "%(num)d question"
msgid_plural "%(num)d questions"
msgstr[0] "%(num)d вопрос"
msgstr[1] "%(num)d вопроса"
msgstr[2] "%(num)d вопросов"

msgid "%(count)s day in a row"
msgid_plural "%(count)s days in a row"
msgstr[0] "%(count)s день подряд"
msgstr[1] "%(count)s дня подряд"
msgstr[2] "%(count)s дней подряд"

#, fuzzy
msgid "Log out"
msgstr "Выйти"
"""


@pytest.fixture
def ru_catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    po = tmp_path / "messages.po"
    po.write_text(RU_PO, encoding="utf-8")
    monkeypatch.setitem(i18n.catalogs, "ru", load_catalog(po))


@pytest.mark.parametrize(
    ("cookie", "header", "expected"),
    [
        ("uz", "ru-RU,ru;q=0.9", "uz"),
        ("de", "ru-RU,ru;q=0.9", "ru"),
        (None, "de-DE,en;q=0.5,uz;q=0.8", "uz"),
        (None, "uz-Latn-UZ", "uz"),
        (None, "de-DE, fr;q=0.9", "en"),
        (None, "ru;q=0, en;q=0.1", "en"),
        (None, None, "en"),
    ],
    ids=[
        "cookie wins",
        "unknown cookie ignored",
        "highest weight we have",
        "region and script",
        "nothing we have",
        "q=0 means no",
        "nothing sent",
    ],
)
def test_pick_locale(cookie: str | None, header: str | None, expected: str) -> None:
    assert pick_locale(cookie, header) == expected


@pytest.mark.usefixtures("ru_catalog")
def test_python_and_templates_translate_into_the_current_language() -> None:
    days = templates.env.from_string(
        "{% trans count=n %}{{ count }} day in a row"
        "{% pluralize %}{{ count }} days in a row{% endtrans %}"
    )

    with use_locale("ru"):
        assert _("Hello, %(name)s!", name="Damir") == "Привет, Damir!"
        assert _("Log out") == "Log out"  # fuzzy: not trusted yet
        assert [
            ngettext("%(num)d question", "%(num)d questions", n) for n in (1, 3, 11, 21)
        ] == [
            "1 вопрос",
            "3 вопроса",
            "11 вопросов",
            "21 вопрос",
        ]
        assert [days.render(n=n) for n in (1, 3, 5)] == [
            "1 день подряд",
            "3 дня подряд",
            "5 дней подряд",
        ]

    assert days.render(n=5) == "5 days in a row"


def test_concurrent_requests_keep_their_own_language() -> None:
    app = FastAPI()
    app.add_middleware(LocaleMiddleware)

    @app.get("/locale")
    def locale() -> str:
        time.sleep(0.02)
        return current_locale()

    async def ask_all(codes: list[str]) -> list[str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t"
        ) as client:
            responses = await asyncio.gather(
                *(
                    client.get(
                        "/locale", headers={"cookie": f"{i18n.LOCALE_COOKIE}={c}"}
                    )
                    for c in codes
                )
            )
        return [r.json() for r in responses]

    codes = ["ru", "uz", "en"] * 10
    assert asyncio.run(ask_all(codes)) == codes
