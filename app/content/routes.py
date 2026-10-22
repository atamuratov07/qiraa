from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.auth.deps import CurrentUser
from app.auth.models import User
from app.content.errors import ContentError, describe
from app.content.loader import MAX_BYTES, decode, parse
from app.content.prompt import chatbot_prompt
from app.content.service import ImportReport, import_passages
from app.content.views import ImportPage, ShownError
from app.core.db import DB
from app.core.templating import render

router = APIRouter(tags=["content"])


def page(
    user: User,
    *,
    text: str = "",
    common: bool = False,
    errors: list[ShownError] | None = None,
    report: ImportReport | None = None,
) -> ImportPage:
    return {
        "user": user,
        "text": text,
        "common": common,
        "errors": errors or [],
        "report": report,
        "prompt": chatbot_prompt(),
    }


@router.get("/manage/import")
def import_page(request: Request, user: CurrentUser) -> HTMLResponse:
    return render(request, "content/import.html", page(user))


@router.post("/manage/import")
def import_content(
    request: Request,
    db: DB,
    user: CurrentUser,
    text: Annotated[str, Form()] = "",
    common: Annotated[bool, Form()] = False,
    file: Annotated[UploadFile | None, File()] = None,
) -> HTMLResponse:
    common = common and user.is_admin

    try:
        if file is not None and file.filename:
            text = decode(file.file.read(MAX_BYTES + 1))
        report = import_passages(db, parse(text).passages, owner=user, common=common)

    except ContentError as e:
        errors = [ShownError(err.line, err.path, describe(err)) for err in e.errors]
        ctx = page(user, text=text, common=common, errors=errors)

        return render(request, "content/import.html", ctx, status_code=400)

    return render(
        request, "content/import.html", page(user, common=common, report=report)
    )
