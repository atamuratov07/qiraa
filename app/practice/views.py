from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.practice.models import Attempt, AttemptContent


@dataclass(frozen=True, slots=True)
class UnfinishedInfo:
    id: int
    answered: int
    total: int
    elapsed_seconds: int


class AttemptPage(TypedDict):
    """{passages,grammar}/attempt.html, GET /attempts/{attempt_id} while it is open"""

    user: User
    title: str
    passage_id: int | None
    content: AttemptContent
    attempt: Attempt
    answers: dict[int, int]
    paused: bool


class ResultPage(TypedDict):
    """{passages,grammar}/result.html, GET /attempts/{attempt_id} once submitted"""

    user: User
    title: str
    passage_id: int | None
    content: AttemptContent
    attempt: Attempt
    answers: dict[int, int]
