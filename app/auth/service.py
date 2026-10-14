import hmac
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, not_, select
from sqlalchemy.orm import Session

from app.auth.models import User, UserSession
from app.auth.security import (
    hash_password,
    hash_token,
    needs_rehash,
    new_session_token,
    verify_password,
    waste_equal_time,
)
from app.core.config import get_settings
from app.core.i18n import _
from app.passages.models import Passage

SESSION_COOKIE = "qiraa_session"
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128


class AuthError(ValueError):
    """A message safe to show on the form."""


def normalize_username(raw: str) -> str:
    return raw.strip().lower()


def signup_code() -> str:
    code = get_settings().signup_code
    return code.get_secret_value() if code else ""


def register(
    db: Session, username: str, password: str, password_confirm: str, code: str = ""
) -> User:
    expected = signup_code()
    if expected and not hmac.compare_digest(code.strip().encode(), expected.encode()):
        raise AuthError(_("Wrong invite code."))

    username = normalize_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise AuthError(_("Username: 3–32 characters, Latin letters, digits or _."))
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise AuthError(
            _(
                "The password must be %(min)d–%(max)d characters long.",
                min=MIN_PASSWORD,
                max=MAX_PASSWORD,
            )
        )
    if password != password_confirm:
        raise AuthError(_("The passwords don't match."))
    if db.scalar(select(User.id).where(User.username == username)):
        raise AuthError(_("This username is already taken."))

    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None:
        waste_equal_time(password)
        raise AuthError(_("Wrong username or password."))
    if not verify_password(user.password_hash, password):
        raise AuthError(_("Wrong username or password."))
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
    return user


def set_admin(db: Session, username: str) -> User | None:
    """Returns None when there's no such user."""
    user = db.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None:
        return None

    user.is_admin = True
    db.commit()
    return user


def create_session(db: Session, user: User) -> str:
    token, token_hash = new_session_token()
    days = get_settings().session_days
    db.add(
        UserSession(
            token_hash=token_hash,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=days),
        )
    )
    db.commit()
    return token


def user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    )
    if session is None:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        db.delete(session)
        db.commit()
        return None
    return session.user


def destroy_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(
            delete(UserSession).where(UserSession.token_hash == hash_token(token))
        )
        db.commit()


def delete_account(db: Session, user: User, password: str) -> None:
    if not verify_password(user.password_hash, password):
        raise AuthError(_("Wrong password."))

    db.execute(
        delete(Passage).where(Passage.owner_id == user.id, not_(Passage.is_common))
    )

    db.delete(user)
    db.commit()
