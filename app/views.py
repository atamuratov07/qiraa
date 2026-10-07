"""
Rule (Jinja runs with StrictUndefined, see templating.py): every key is required.
Optional values are typed `X | None` and passed as None, never left out.
"""

import datetime as dt
from dataclasses import dataclass
from typing import TypedDict

from app.models import Attempt, Option, Passage, User

# ---------------------------------------------------------------------------
# View models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnfinishedInfo:
    id: int
    answered: int
    total: int
    elapsed_seconds: int


@dataclass(frozen=True, slots=True)
class PassageCard:
    id: int
    title: str
    level: str
    question_count: int
    best: int | None
    tries: int
    unfinished: UnfinishedInfo | None


@dataclass(frozen=True, slots=True)
class QuestionView:
    id: int
    prompt: str
    explanation: str | None
    options: list[Option]


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


# ---------------------------------------------------------------------------
# Page contexts
# ---------------------------------------------------------------------------


class PassagesPage(TypedDict):
    """passages.html, GET /passages"""

    user: User
    streak: int
    passages: list[PassageCard]


class PassageStartPage(TypedDict):
    """passage_start.html, GET /passages/{passage_id} when there is no open attempt"""

    user: User
    passage: Passage
    question_count: int
    best: int | None
    tries: int


class AttemptPage(TypedDict):
    """attempt.html, GET /attempts/{attempt_id} while the attempt is open"""

    user: User
    passage: Passage
    attempt: Attempt
    questions: list[QuestionView]
    answers: dict[int, int]
    paused: bool


class ResultPage(TypedDict):
    """result.html, GET /attempts/{attempt_id} once submitted"""

    user: User
    passage: Passage
    attempt: Attempt
    questions: list[QuestionView]
    answers: dict[int, int]


class ProfilePage(TypedDict):
    """profile.html, GET /profile (and POST /account/delete on a wrong password)"""

    user: User
    streak: int
    longest_streak: int
    stats: ProfileStats
    recent: list[Attempt]
    calendar: list[CalendarDay] | None
    delete_error: str | None


class LoginPage(TypedDict):
    """login.html, GET and POST /login"""

    user: None  # base.html reads `user`; nobody is logged in on this page
    error: str | None
    username: str | None
    next: str


class SignupPage(TypedDict):
    """signup.html, GET and POST /signup"""

    user: None
    error: str | None
    username: str | None


class ErrorPage(TypedDict):
    """error.html, rendered by an exception handler for 404 and similar"""

    user: User | None
    status_code: int
    message: str
