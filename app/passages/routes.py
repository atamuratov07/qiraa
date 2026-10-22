from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.deps import CurrentUser
from app.core.db import DB
from app.core.i18n import _
from app.core.permissions import load_editable
from app.core.templating import render
from app.core.timeutils import local_day
from app.passages.models import Passage
from app.passages.service import (
    delete_passage,
    load_passage,
    managed_passages,
    passage_cards,
    passage_stats,
)
from app.passages.views import ManagePage, PassagesPage, PassageStartPage
from app.practice.service import open_attempt_for, start
from app.profile.streaks import visible_streak

router = APIRouter(tags=["passages"])


@router.get("/passages")
def passages(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    ctx: PassagesPage = {
        "user": user,
        "streak": visible_streak(user, local_day(datetime.now(UTC))),
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
def start_attempt(pid: int, db: DB, user: CurrentUser) -> RedirectResponse:
    passage = load_passage(db, user, pid)
    if passage is None:
        raise HTTPException(404, _("Passage not found"))

    attempt = start(db, user, passage, now=datetime.now(UTC))
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
