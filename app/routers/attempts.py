from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db import DB
from app.deps import CurrentUser, FormFields
from app.models import Attempt, User
from app.redirects import safe_next
from app.services import attempts
from app.templating import render
from app.views import AttemptPage, ResultPage

router = APIRouter(tags=["attempts"])


def _own_attempt(db: DB, user: User, attempt_id: int) -> Attempt:
    attempt = attempts.load_attempt(db, user, attempt_id)
    if attempt is None:
        raise HTTPException(404, "Attempt not found")

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
    questions = attempts.ordered_questions(attempt)
    answers = attempts.saved_answers(attempt)

    if attempt.submitted_at is not None:
        result_ctx: ResultPage = {
            "user": user,
            "passage": attempt.passage,
            "attempt": attempt,
            "questions": questions,
            "answers": answers,
        }
        return render(request, "result.html", result_ctx)

    ctx: AttemptPage = {
        "user": user,
        "passage": attempt.passage,
        "attempt": attempt,
        "questions": questions,
        "answers": answers,
        "paused": attempts.is_paused(attempt, datetime.now(UTC)),
    }
    return render(request, "attempt.html", ctx)


@router.post("/attempts/{aid}/submit")
def submit_attempt(
    aid: int, fields: FormFields, db: DB, user: CurrentUser
) -> RedirectResponse:
    attempt = _own_attempt(db, user, aid)

    attempts.submit(db, attempt, _answers_from_form(fields), datetime.now(UTC))

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
        attempts.discard(db, attempt)
    except attempts.AttemptClosed as exc:
        raise HTTPException(409, str(exc)) from exc

    return RedirectResponse(safe_next(next), status_code=303)


@router.post("/attempts/{aid}/delete")
def delete_attempt(
    aid: int,
    db: DB,
    user: CurrentUser,
    next: Annotated[str, Form()] = "/profile",
) -> RedirectResponse:
    attempt = attempts.load_attempt(db, user, aid, with_content=False)
    if attempt is None:
        raise HTTPException(404, "Attempt not found")

    attempts.delete(db, attempt)

    return RedirectResponse(safe_next(next, default="/profile"), status_code=303)
