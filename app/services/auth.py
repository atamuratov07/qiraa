import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User, UserSession
from app.security import (
    hash_password,
    hash_token,
    needs_rehash,
    new_session_token,
    verify_password,
    waste_equal_time,
)

SESSION_COOKIE = "qiraa_session"
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128


class AuthError(ValueError):
    """A message safe to show on the form."""


def normalize_username(raw: str) -> str:
    return raw.strip().lower()


def register(db: Session, username: str, password: str, password_confirm: str) -> User:
    username = normalize_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise AuthError("Имя пользователя: 3–32 символа, латинские буквы, цифры или _.")
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise AuthError(
            f"Пароль должен содержать {MIN_PASSWORD}–{MAX_PASSWORD} символов."
        )
    if password != password_confirm:
        raise AuthError("Пароли не совпадают.")
    if db.scalar(select(User.id).where(User.username == username)):
        raise AuthError("Это имя пользователя уже занято.")

    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None:
        waste_equal_time(password)
        raise AuthError("Неверное имя пользователя или пароль.")
    if not verify_password(user.password_hash, password):
        raise AuthError("Неверное имя пользователя или пароль.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
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
    if expires.tzinfo is None:  # SQLite drops tz info; values were written as UTC
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        db.delete(session)
        db.commit()
        return None
    return session.user


def destroy_session(db: Session, token: str | None) -> None:
    if token:
        _ = db.execute(
            delete(UserSession).where(UserSession.token_hash == hash_token(token))
        )
        db.commit()


def delete_account(db: Session, user: User, password: str) -> None:
    if not verify_password(user.password_hash, password):
        raise AuthError("Неверный пароль.")

    db.delete(user)
    db.commit()
