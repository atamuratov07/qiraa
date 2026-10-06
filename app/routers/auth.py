from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.db import DB
from app.deps import MaybeUser
from app.models import User
from app.services import auth
from app.templating import templates

router = APIRouter()


def _safe_next(next_url: str | None) -> str:
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


def _login_response(db: DB, user: User, next_url: str = "/") -> RedirectResponse:
    token = auth.create_session(db, user)
    settings = get_settings()
    response = RedirectResponse(_safe_next(next_url), status_code=303)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=settings.session_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
    )
    return response


@router.get("/signup")
def signup_page(request: Request, user: MaybeUser):
    if user:
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request,
        "signup.html",
        status_code=200,
    )


@router.post("/signup")
def signup(
    request: Request,
    db: DB,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    password_confirm: Annotated[str, Form()],
):
    try:
        user = auth.register(db, username, password, password_confirm)
    except auth.AuthError as exc:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"error": str(exc), "username": username},
            status_code=400,
        )
    return _login_response(db, user)


@router.get("/login")
def login_page(request: Request, user: MaybeUser, next: str = "/"):
    if user:
        return RedirectResponse(_safe_next(next), status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "next": next,
        },
    )


@router.post("/login")
def login(
    request: Request,
    db: DB,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/",
):
    try:
        user = auth.authenticate(db, username, password)
    except auth.AuthError as exc:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": str(exc), "username": username, "next": next},
            status_code=400,
        )
    return _login_response(db, user, next)


@router.post("/logout")
def logout(request: Request, db: DB):
    auth.destroy_session(db, request.cookies.get(auth.SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(auth.SESSION_COOKIE)
    return response
