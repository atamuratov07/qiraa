from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.deps import CurrentUser
from app.auth.models import User
from app.core.db import DB
from app.core.deps import FormFields
from app.core.redirects import safe_next
from app.core.templating import render
from app.practice import service
from app.practice.models import Attempt
from app.practice.views import AttemptPage, ResultPage

router = APIRouter(tags=["attempts"])


def _own_attempt(db: DB, user: User, attempt_id: int) -> Attempt:
    attempt = service.load_attempt(db, user, attempt_id)
    if attempt is None:
        raise HTTPException(404, "Попытка не найдена")

    return attempt


def _answers_from_form(fields: dict[str, str]) -> dict[int, int]:
    answers: dict[int, int] = {}
    for name, value in fields.items():
        if not name.startswith("q"):
            continue
        try:
            answers[int(name.removeprefix("q"))] = int(value)
        except ValueError:
            continue

    return answers


@router.get("/attempts/{aid}")
def attempt_page(request: Request, aid: int, db: DB, user: CurrentUser) -> HTMLResponse:
    attempt = _own_attempt(db, user, aid)
    questions = service.ordered_questions(attempt)
    answers = service.saved_answers(attempt)

    if attempt.submitted_at is not None:
        result_ctx: ResultPage = {
            "user": user,
            "passage": attempt.passage,
            "attempt": attempt,
            "questions": questions,
            "answers": answers,
        }
        return render(request, "practice/result.html", result_ctx)

    ctx: AttemptPage = {
        "user": user,
        "passage": attempt.passage,
        "attempt": attempt,
        "questions": questions,
        "answers": answers,
        "paused": service.is_paused(attempt, datetime.now(UTC)),
    }
    return render(request, "practice/attempt.html", ctx)


@router.post("/attempts/{aid}/submit")
def submit_attempt(
    aid: int, fields: FormFields, db: DB, user: CurrentUser
) -> RedirectResponse:
    attempt = _own_attempt(db, user, aid)

    service.submit(db, attempt, _answers_from_form(fields), datetime.now(UTC))

    return RedirectResponse(f"/attempts/{attempt.id}", status_code=303)


@router.post("/attempts/{aid}/discard")
def discard_attempt(
    aid: int,
    db: DB,
    user: CurrentUser,
    next: Annotated[str, Form()] = "/passages",
) -> RedirectResponse:
    attempt = _own_attempt(db, user, aid)

    try:
        service.discard(db, attempt)
    except service.AttemptClosed as exc:
        raise HTTPException(409, str(exc)) from exc

    return RedirectResponse(safe_next(next), status_code=303)


@router.post("/attempts/{aid}/delete")
def delete_attempt(
    aid: int,
    db: DB,
    user: CurrentUser,
    next: Annotated[str, Form()] = "/profile",
) -> RedirectResponse:
    attempt = service.load_attempt(db, user, aid, with_content=False)
    if attempt is None:
        raise HTTPException(404, "Попытка не найдена")

    service.delete(db, attempt)

    return RedirectResponse(safe_next(next, default="/profile"), status_code=303)
