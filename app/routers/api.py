"""JSON endpoints used by static/attempt.js. Errors come back as JSON: {"detail": "..."}."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response

from app.db import DB
from app.deps import CurrentUser
from app.models import Attempt, User
from app.schemas import AnswerIn, HeartbeatOut
from app.services import attempts

router = APIRouter(prefix="/api", tags=["api"])


def _own_attempt(db: DB, user: User, attempt_id: int) -> Attempt:
    attempt = attempts.load_attempt(db, user, attempt_id, with_content=False)
    if attempt is None:
        raise HTTPException(404, "Attempt not found")

    return attempt


@router.post("/attempts/{attempt_id}/heartbeat")
def heartbeat(attempt_id: int, db: DB, user: CurrentUser) -> HeartbeatOut:
    attempt = _own_attempt(db, user, attempt_id)

    try:
        elapsed = attempts.heartbeat(db, attempt, now=datetime.now(UTC))
    except attempts.AttemptClosed as exc:
        raise HTTPException(409, str(exc)) from exc

    return HeartbeatOut(elapsed_seconds=elapsed)


@router.put("/attempts/{attempt_id}/answers/{question_id}", status_code=204)
def save_answer(
    attempt_id: int, question_id: int, body: AnswerIn, db: DB, user: CurrentUser
) -> Response:
    attempt = _own_attempt(db, user, attempt_id)

    try:
        attempts.save_answer(db, attempt, question_id, body.option_id)
    except attempts.AttemptClosed as exc:
        raise HTTPException(409, str(exc)) from exc
    except attempts.BadAnswer as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(status_code=204)
