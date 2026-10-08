from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.db import DB
from app.deps import CurrentUser
from app.services.profile import profile_context
from app.templating import render

router = APIRouter(tags=["profile"])


@router.get("/profile")
def profile_page(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    return render(request, "profile.html", profile_context(db, user, datetime.now(UTC)))
