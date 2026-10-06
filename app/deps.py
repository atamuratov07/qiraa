from typing import Annotated

from fastapi import Depends, Request

from app.db import DB
from app.models import User
from app.services import auth


class LoginRequired(Exception):
    """Raised by `require_user`; main.py turns it into a redirect (or a 401 for /api)."""


def optional_user(request: Request, db: DB) -> User | None:
    return auth.user_from_token(db, request.cookies.get(auth.SESSION_COOKIE))


def require_user(request: Request, db: DB) -> User:
    token = request.cookies.get(auth.SESSION_COOKIE)
    user = auth.user_from_token(db, token)
    if user is None:
        raise LoginRequired

    return user


CurrentUser = Annotated[User, Depends(require_user)]
MaybeUser = Annotated[User | None, Depends(optional_user)]
