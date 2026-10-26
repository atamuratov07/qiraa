from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.auth.deps import CurrentUser
from app.auth.models import User
from app.content.errors import ContentError, describe
from app.content.loader import MAX_BYTES, decode, parse
from app.content.service import ImportReport
from app.content.views import ImportKind, ImportPage, ShownError
from app.core.db import DB
from app.core.templating import render
from app.grammar.prompt import grammar_prompt
from app.grammar.schemas import GrammarFile
from app.grammar.service import import_grammar
from app.passages.prompt import passage_prompt
from app.passages.schemas import PassageFile
from app.passages.service import import_passages

PROMPTS: dict[ImportKind, Callable[[], str]] = {
    "passages": passage_prompt,
    "grammar": grammar_prompt,
}

router = APIRouter(tags=["content"])


def page(
    user: User,
    kind: ImportKind,
    *,
    text: str = "",
    common: bool = False,
    errors: list[ShownError] | None = None,
    report: ImportReport | None = None,
) -> ImportPage:
    return {
        "user": user,
        "kind": kind,
        "text": text,
        "common": common,
        "errors": errors or [],
        "report": report,
        "prompt": PROMPTS[kind](),
    }


def run_import(
    request: Request,
    db: DB,
    user: User,
    kind: ImportKind,
    *,
    text: str,
    file: UploadFile | None,
    common: bool,
) -> HTMLResponse:
    common = common and user.is_admin

    try:
        if file is not None and file.filename:  # no file chosen: filename is ""
            text = decode(file.file.read(MAX_BYTES + 1))

        if kind == "passages":
            entries = parse(text, PassageFile).passages
            report = import_passages(db, entries, owner=user, common=common)
        else:
            questions = parse(text, GrammarFile).grammar
            report = import_grammar(db, questions, owner=user, common=common)

    except ContentError as e:
        errors = [ShownError(err.line, err.path, describe(err)) for err in e.errors]
        ctx = page(user, kind, text=text, common=common, errors=errors)

        return render(request, "content/import.html", ctx, status_code=400)

    ctx = page(user, kind, common=common, report=report)
    return render(request, "content/import.html", ctx)


@router.get("/manage/passages/import")
def passages_import_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return render(request, "content/import.html", page(user, "passages"))


@router.post("/manage/passages/import")
def passages_import(
    request: Request,
    db: DB,
    user: CurrentUser,
    text: Annotated[str, Form()] = "",
    common: Annotated[bool, Form()] = False,
    file: Annotated[UploadFile | None, File()] = None,
) -> HTMLResponse:
    return run_import(
        request, db, user, "passages", text=text, file=file, common=common
    )


@router.get("/manage/grammar/import")
def grammar_import_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return render(request, "content/import.html", page(user, "grammar"))


@router.post("/manage/grammar/import")
def grammar_import(
    request: Request,
    db: DB,
    user: CurrentUser,
    text: Annotated[str, Form()] = "",
    common: Annotated[bool, Form()] = False,
    file: Annotated[UploadFile | None, File()] = None,
) -> HTMLResponse:
    return run_import(request, db, user, "grammar", text=text, file=file, common=common)
