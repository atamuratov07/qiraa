from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.db import DB
from app.deps import CurrentUser
from app.services import attempts, streaks
from app.templating import render
from app.timeutils import local_day
from app.views import PassagesPage, PassageStartPage

router = APIRouter(tags=["passages"])


@router.get("/passages")
def passages(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    ctx: PassagesPage = {
        "user": user,
        "streak": streaks.visible_streak(user, local_day(datetime.now(UTC))),
        "passages": attempts.passage_cards(db, user),
    }
    return render(request, "passages.html", ctx)


@router.get("/passages/{pid}", response_model=None)
def passage_start(
    request: Request, pid: int, db: DB, user: CurrentUser
) -> HTMLResponse | RedirectResponse:
    passage = attempts.load_passage(db, pid)
    if passage is None:
        raise HTTPException(404, "Passage not found")

    existing = attempts.open_attempt_for(db, user, passage)
    if existing is not None:
        return RedirectResponse(f"/attempts/{existing.id}", status_code=303)

    best, tries = attempts.passage_stats(db, user, passage)
    ctx: PassageStartPage = {
        "user": user,
        "passage": passage,
        "question_count": len(passage.questions),
        "best": best,
        "tries": tries,
    }
    return render(request, "passage_start.html", ctx)


@router.post("/passages/{pid}/attempts")
def start_attempt(pid: int, db: DB, user: CurrentUser) -> RedirectResponse:
    passage = attempts.load_passage(db, pid)
    if passage is None:
        raise HTTPException(404, "Passage not found")

    attempt = attempts.start(db, user, passage, now=datetime.now(UTC))
    return RedirectResponse(f"/attempts/{attempt.id}", status_code=303)
