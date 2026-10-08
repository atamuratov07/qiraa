from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import DB
from app.deps import CurrentUser, MaybeUser
from app.models import User
from app.redirects import safe_next
from app.services import auth
from app.services.profile import profile_context
from app.templating import render
from app.views import LoginPage, SignupPage

router = APIRouter(tags=["auth"])


def _login_response(
    db: Session, user: User, next_url: str | None = None
) -> RedirectResponse:
    token = auth.create_session(db, user)
    settings = get_settings()
    response = RedirectResponse(safe_next(next_url), status_code=303)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    return response


def _require_signup_open() -> None:
    if not get_settings().allow_signup:
        raise HTTPException(403, "Регистрация закрыта.")


@router.get("/signup", response_model=None)
def signup_page(request: Request, user: MaybeUser) -> HTMLResponse | RedirectResponse:
    if user is not None:
        return RedirectResponse("/passages", status_code=303)

    _require_signup_open()

    ctx: SignupPage = {"user": None, "username": None, "error": None}
    return render(request, "signup.html", ctx)


@router.post("/signup", response_model=None)
def signup(
    request: Request,
    db: DB,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    password_confirm: Annotated[str, Form()],
) -> HTMLResponse | RedirectResponse:
    _require_signup_open()

    try:
        user = auth.register(db, username, password, password_confirm)
    except auth.AuthError as exc:
        ctx: SignupPage = {"user": None, "username": username, "error": str(exc)}
        return render(request, "signup.html", ctx, status_code=400)

    return _login_response(db, user)


@router.get("/login", response_model=None)
def login_page(
    request: Request, user: MaybeUser, next: str = "/passages"
) -> HTMLResponse | RedirectResponse:
    if user is not None:
        return RedirectResponse(safe_next(next), status_code=303)

    ctx: LoginPage = {
        "user": None,
        "username": None,
        "error": None,
        "next": safe_next(next),
    }
    return render(request, "login.html", ctx)


@router.post("/login", response_model=None)
def login(
    request: Request,
    db: DB,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/passages",
) -> HTMLResponse | RedirectResponse:
    try:
        user = auth.authenticate(db, username, password)
    except auth.AuthError as exc:
        ctx: LoginPage = {
            "user": None,
            "username": username,
            "error": str(exc),
            "next": safe_next(next),
        }
        return render(request, "login.html", ctx, status_code=400)

    return _login_response(db, user, next)


@router.post("/logout")
def logout(request: Request, db: DB) -> RedirectResponse:
    auth.destroy_session(db, request.cookies.get(auth.SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.SESSION_COOKIE)
    return response


@router.post("/account/delete", response_model=None)
def delete_account(
    request: Request, db: DB, user: CurrentUser, password: Annotated[str, Form()]
) -> HTMLResponse | RedirectResponse:
    try:
        auth.delete_account(db, user, password)
    except auth.AuthError as exc:
        ctx = profile_context(db, user, datetime.now(UTC), delete_error=str(exc))
        return render(request, "profile.html", ctx, status_code=400)

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.SESSION_COOKIE)
    return response
