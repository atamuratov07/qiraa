from typing import Annotated

from fastapi import Depends, Request

from app.auth import service
from app.auth.models import User
from app.core.db import DB


class LoginRequired(Exception):
    """Raised by `require_user`; main.py turns it into a redirect (or a 401 for /api)."""


def optional_user(request: Request, db: DB) -> User | None:
    return service.user_from_token(db, request.cookies.get(service.SESSION_COOKIE))


def require_user(request: Request, db: DB) -> User:
    token = request.cookies.get(service.SESSION_COOKIE)
    user = service.user_from_token(db, token)
    if user is None:
        raise LoginRequired

    return user


CurrentUser = Annotated[User, Depends(require_user)]
MaybeUser = Annotated[User | None, Depends(optional_user)]
