from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import selectinload

from app.auth.deps import CurrentUser
from app.auth.models import User
from app.content.editor import EDITOR_MESSAGES, posted
from app.content.errors import messages_by_path
from app.content.service import SlugTaken
from app.core.db import DB
from app.core.i18n import _
from app.core.permissions import load_editable
from app.core.templating import render
from app.passages.models import Passage, PassageQuestion
from app.passages.schemas import PassageIn
from app.passages.service import (
    create_passage,
    delete_passage,
    load_passage,
    managed_passages,
    open_attempt_for,
    passage_cards,
    passage_in,
    passage_stats,
    start_attempt,
    update_passage,
)
from app.passages.views import (
    EDITOR_LIMITS,
    EditorPage,
    ManagePage,
    PassagesPage,
    PassageStartPage,
)


def render_editor(
    request: Request,
    user: User,
    passage: Passage | None,
    *,
    data: dict[str, object] | None,
    common: bool,
    errors: dict[str, str] | None = None,
) -> HTMLResponse:
    ctx: EditorPage = {
        "user": user,
        "passage_id": passage.id if passage else None,
        "slug": passage.slug if passage else None,
        "common": common,
        "data": data,
        "errors": errors or {},
        "limits": EDITOR_LIMITS,
    }
    status_code = 400 if errors else 200

    return render(request, "passages/editor.html", ctx, status_code=status_code)


def load_for_editing(db: DB, user: User, pid: int) -> Passage:
    passage = load_editable(
        db,
        user,
        Passage,
        pid,
        selectinload(Passage.questions).selectinload(PassageQuestion.options),
    )
    if passage is None:
        raise HTTPException(404, _("Passage not found"))

    return passage


router = APIRouter(tags=["passages"])


@router.get("/passages")
def passages(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    ctx: PassagesPage = {
        "user": user,
        "passages": passage_cards(db, user),
    }
    return render(request, "passages/list.html", ctx)


@router.get("/passages/{pid}", response_model=None)
def passage_start(
    request: Request, pid: int, db: DB, user: CurrentUser
) -> HTMLResponse | RedirectResponse:
    passage = load_passage(db, user, pid)
    if passage is None:
        raise HTTPException(404, _("Passage not found"))

    existing = open_attempt_for(db, user, passage)
    if existing is not None:
        return RedirectResponse(f"/attempts/{existing.id}", status_code=303)

    best, tries = passage_stats(db, user, passage)
    ctx: PassageStartPage = {
        "user": user,
        "passage": passage,
        "question_count": len(passage.questions),
        "best": best,
        "tries": tries,
    }
    return render(request, "passages/start.html", ctx)


@router.post("/passages/{pid}/attempts")
def new_attempt(pid: int, db: DB, user: CurrentUser) -> RedirectResponse:
    passage = load_passage(db, user, pid)
    if passage is None:
        raise HTTPException(404, _("Passage not found"))

    attempt = start_attempt(db, user, passage, now=datetime.now(UTC))
    return RedirectResponse(f"/attempts/{attempt.id}", status_code=303)


@router.get("/manage/passages")
def manage_page(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    ctx: ManagePage = {"user": user, "passages": managed_passages(db, user)}

    return render(request, "passages/manage.html", ctx)


@router.post("/manage/passages/{pid}/delete")
def manage_delete(pid: int, db: DB, user: CurrentUser) -> RedirectResponse:
    passage = load_editable(db, user, Passage, pid)

    if passage is None:
        raise HTTPException(404, _("Passage not found"))

    delete_passage(db, passage)

    return RedirectResponse("/manage/passages", status_code=303)


@router.get("/manage/passages/new")
def manage_new(request: Request, user: CurrentUser) -> HTMLResponse:
    return render_editor(request, user, None, data=None, common=False)


@router.post("/manage/passages/new", response_model=None)
def manage_create(
    request: Request,
    db: DB,
    user: CurrentUser,
    passage: Annotated[str, Form()],
    common: Annotated[bool, Form()] = False,
) -> HTMLResponse | RedirectResponse:
    try:
        data = PassageIn.model_validate_json(passage)
    except ValidationError as e:
        errors = messages_by_path(e, EDITOR_MESSAGES)
        return render_editor(
            request, user, None, data=posted(passage), common=common, errors=errors
        )

    create_passage(db, user, data, common=common)

    return RedirectResponse("/manage/passages", status_code=303)


@router.get("/manage/passages/{pid}/edit")
def manage_edit(request: Request, pid: int, db: DB, user: CurrentUser) -> HTMLResponse:
    existing = load_for_editing(db, user, pid)
    data = passage_in(existing).model_dump()

    return render_editor(request, user, existing, data=data, common=existing.is_common)


@router.post("/manage/passages/{pid}/edit", response_model=None)
def manage_update(
    request: Request,
    pid: int,
    db: DB,
    user: CurrentUser,
    passage: Annotated[str, Form()],
    common: Annotated[bool, Form()] = False,
) -> HTMLResponse | RedirectResponse:
    existing = load_for_editing(db, user, pid)

    try:
        data = PassageIn.model_validate_json(passage)
    except ValidationError as e:
        errors = messages_by_path(e, EDITOR_MESSAGES)
        return render_editor(
            request, user, existing, data=posted(passage), common=common, errors=errors
        )

    try:
        update_passage(db, user, existing, data, common=common)
    except SlugTaken as e:
        errors = {"": _("Another passage already uses the slug %(slug)s.", slug=e.slug)}
        return render_editor(
            request,
            user,
            existing,
            data=data.model_dump(),
            common=common,
            errors=errors,
        )

    return RedirectResponse("/manage/passages", status_code=303)
