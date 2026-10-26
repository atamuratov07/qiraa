import datetime as dt
from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.practice.models import Attempt


@dataclass(frozen=True, slots=True)
class ProfileStats:
    attempts: int
    answered: int
    accuracy: int | None
    passages_done: int
    passages_total: int


@dataclass(frozen=True, slots=True)
class CalendarDay:
    date: dt.date
    count: int


class ProfilePage(TypedDict):
    """profile/profile.html, GET /profile (and POST /account/delete on a wrong password)"""

    user: User
    streak: int
    longest_streak: int
    stats: ProfileStats
    recent: list[Attempt]
    calendar: list[CalendarDay] | None
    delete_error: str | None
