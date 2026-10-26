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
from app.content.schemas import QuestionIn
from app.content.service import SlugTaken
from app.core.db import DB
from app.core.i18n import _
from app.core.permissions import load_editable
from app.core.templating import render
from app.grammar.models import GrammarQuestion
from app.grammar.service import (
    EmptyPool,
    Pool,
    create_question,
    delete_question,
    managed_questions,
    question_in,
    start_page,
    start_session,
    update_question,
)
from app.grammar.views import EDITOR_LIMITS, EditorPage, ManagePage


def render_editor(
    request: Request,
    user: User,
    question: GrammarQuestion | None,
    *,
    data: dict[str, object] | None,
    common: bool,
    errors: dict[str, str] | None = None,
) -> HTMLResponse:
    ctx: EditorPage = {
        "user": user,
        "question_id": question.id if question else None,
        "slug": question.slug if question else None,
        "common": common,
        "data": data,
        "errors": errors or {},
        "limits": EDITOR_LIMITS,
    }
    status_code = 400 if errors else 200

    return render(request, "grammar/editor.html", ctx, status_code=status_code)


def load_for_editing(db: DB, user: User, qid: int) -> GrammarQuestion:
    question = load_editable(
        db,
        user,
        GrammarQuestion,
        qid,
        selectinload(GrammarQuestion.options),
    )
    if question is None:
        raise HTTPException(404, _("Question not found"))

    return question


router = APIRouter(tags=["grammar"])


@router.get("/grammar")
def grammar_page(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    return render(request, "grammar/start.html", start_page(db, user))


@router.post("/grammar/sessions", response_model=None)
def new_session(
    request: Request,
    db: DB,
    user: CurrentUser,
    pool: Annotated[Pool, Form()],
    size: Annotated[int, Form(ge=1)] = 10,
) -> RedirectResponse | HTMLResponse:
    try:
        attempt = start_session(db, user, pool, size, now=datetime.now(UTC))
    except EmptyPool:
        ctx = start_page(db, user, empty_pool=True)
        return render(request, "grammar/start.html", ctx, status_code=400)

    return RedirectResponse(f"/attempts/{attempt.id}", status_code=303)


@router.get("/manage/grammar")
def manage_page(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    ctx: ManagePage = {"user": user, "questions": managed_questions(db, user)}

    return render(request, "grammar/manage.html", ctx)


@router.post("/manage/grammar/{qid}/delete")
def manage_delete(qid: int, db: DB, user: CurrentUser) -> RedirectResponse:
    question = load_editable(db, user, GrammarQuestion, qid)

    if question is None:
        raise HTTPException(404, _("Question not found"))

    delete_question(db, question)

    return RedirectResponse("/manage/grammar", status_code=303)


@router.get("/manage/grammar/new")
def manage_new(request: Request, user: CurrentUser) -> HTMLResponse:
    return render_editor(request, user, None, data=None, common=False)


@router.post("/manage/grammar/new", response_model=None)
def manage_create(
    request: Request,
    db: DB,
    user: CurrentUser,
    question: Annotated[str, Form()],
    common: Annotated[bool, Form()] = False,
) -> HTMLResponse | RedirectResponse:
    try:
        data = QuestionIn.model_validate_json(question)
    except ValidationError as e:
        errors = messages_by_path(e, EDITOR_MESSAGES)
        return render_editor(
            request, user, None, data=posted(question), common=common, errors=errors
        )

    create_question(db, user, data, common=common)

    return RedirectResponse("/manage/grammar", status_code=303)


@router.get("/manage/grammar/{qid}/edit")
def manage_edit(request: Request, qid: int, db: DB, user: CurrentUser) -> HTMLResponse:
    existing = load_for_editing(db, user, qid)
    data = question_in(existing).model_dump()

    return render_editor(request, user, existing, data=data, common=existing.is_common)


@router.post("/manage/grammar/{qid}/edit", response_model=None)
def manage_update(
    request: Request,
    qid: int,
    db: DB,
    user: CurrentUser,
    question: Annotated[str, Form()],
    common: Annotated[bool, Form()] = False,
) -> HTMLResponse | RedirectResponse:
    existing = load_for_editing(db, user, qid)

    try:
        data = QuestionIn.model_validate_json(question)
    except ValidationError as e:
        errors = messages_by_path(e, EDITOR_MESSAGES)
        return render_editor(
            request, user, existing, data=posted(question), common=common, errors=errors
        )

    try:
        update_question(db, user, existing, data, common=common)
    except SlugTaken as e:
        errors = {
            "": _("Another question already uses the slug %(slug)s.", slug=e.slug)
        }
        return render_editor(
            request,
            user,
            existing,
            data=data.model_dump(),
            common=common,
            errors=errors,
        )

    return RedirectResponse("/manage/grammar", status_code=303)
