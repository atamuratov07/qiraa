from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.auth.deps import CurrentUser
from app.core.db import DB
from app.core.templating import render
from app.profile.service import profile_context

router = APIRouter(tags=["profile"])


@router.get("/profile")
def profile_page(request: Request, db: DB, user: CurrentUser) -> HTMLResponse:
    return render(
        request, "profile/profile.html", profile_context(db, user, datetime.now(UTC))
    )
