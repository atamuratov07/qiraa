from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.deps import CurrentUser, MaybeUser
from app.auth.models import User
from app.auth.views import LoginPage, SignupPage
from app.core.config import get_settings
from app.core.db import DB
from app.core.redirects import safe_next
from app.core.templating import render
from app.profile.service import profile_context

router = APIRouter(tags=["auth"])


def _login_response(
    db: Session, user: User, next_url: str | None = None
) -> RedirectResponse:
    token = service.create_session(db, user)
    settings = get_settings()
    response = RedirectResponse(safe_next(next_url), status_code=303)
    response.set_cookie(
        service.SESSION_COOKIE,
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
    return render(request, "auth/signup.html", ctx)


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
        user = service.register(db, username, password, password_confirm)
    except service.AuthError as exc:
        ctx: SignupPage = {"user": None, "username": username, "error": str(exc)}
        return render(request, "auth/signup.html", ctx, status_code=400)

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
    return render(request, "auth/login.html", ctx)


@router.post("/login", response_model=None)
def login(
    request: Request,
    db: DB,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/passages",
) -> HTMLResponse | RedirectResponse:
    try:
        user = service.authenticate(db, username, password)
    except service.AuthError as exc:
        ctx: LoginPage = {
            "user": None,
            "username": username,
            "error": str(exc),
            "next": safe_next(next),
        }
        return render(request, "auth/login.html", ctx, status_code=400)

    return _login_response(db, user, next)


@router.post("/logout")
def logout(request: Request, db: DB) -> RedirectResponse:
    service.destroy_session(db, request.cookies.get(service.SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(service.SESSION_COOKIE)
    return response


@router.post("/account/delete", response_model=None)
def delete_account(
    request: Request, db: DB, user: CurrentUser, password: Annotated[str, Form()]
) -> HTMLResponse | RedirectResponse:
    try:
        service.delete_account(db, user, password)
    except service.AuthError as exc:
        ctx = profile_context(db, user, datetime.now(UTC), delete_error=str(exc))
        return render(request, "profile/profile.html", ctx, status_code=400)

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(service.SESSION_COOKIE)
    return response
