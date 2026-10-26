"""JSON errors {"detail": "..."}, in English: the scripts show their own text."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response

from app.auth.deps import CurrentUser
from app.auth.models import User
from app.core.db import DB
from app.practice import service
from app.practice.models import Attempt
from app.practice.schemas import AnswerIn, HeartbeatOut

router = APIRouter(prefix="/api", tags=["api"])


def _own_attempt(db: DB, user: User, attempt_id: int) -> Attempt:
    attempt = service.load_attempt(db, user, attempt_id)
    if attempt is None:
        raise HTTPException(404, "Attempt not found")

    return attempt


@router.post("/attempts/{attempt_id}/heartbeat")
def heartbeat(attempt_id: int, db: DB, user: CurrentUser) -> HeartbeatOut:
    attempt = _own_attempt(db, user, attempt_id)

    try:
        elapsed = service.heartbeat(db, attempt, now=datetime.now(UTC))
    except service.AttemptClosed as exc:
        raise HTTPException(409, str(exc)) from exc

    return HeartbeatOut(elapsed_seconds=elapsed)


@router.put("/attempts/{attempt_id}/answers/{question_id}", status_code=204)
def save_answer(
    attempt_id: int, question_id: int, body: AnswerIn, db: DB, user: CurrentUser
) -> Response:
    attempt = _own_attempt(db, user, attempt_id)

    try:
        service.save_answer(db, attempt, question_id, body.option_id)
    except service.AttemptClosed as exc:
        raise HTTPException(409, str(exc)) from exc
    except service.BadAnswer as exc:
        raise HTTPException(400, str(exc)) from exc

    return Response(status_code=204)
