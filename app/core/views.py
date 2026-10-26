"""
Rule (Jinja runs with StrictUndefined, see templating.py): every key is required.
Optional values are typed `X | None` and passed as None, never left out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from app.auth.models import User


class ErrorPage(TypedDict):
    """error.html, rendered by an exception handler for 404 and similar"""

    user: User | None
    status_code: int
    message: str
