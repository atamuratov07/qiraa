from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth.deps import CurrentUser
from app.core.db import DB
from app.core.templating import render
from app.grammar.service import EmptyPool, Pool, start_page, start_session

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
