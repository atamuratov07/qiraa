from typing import TypedDict

from app.auth.models import User
from app.practice.models import Attempt, AttemptContent


class AttemptPage(TypedDict):
    """practice/attempt.html, GET /attempts/{attempt_id} while the attempt is open"""

    user: User
    title: str
    passage_id: int
    content: AttemptContent
    attempt: Attempt
    answers: dict[int, int]
    paused: bool


class ResultPage(TypedDict):
    """practice/result.html, GET /attempts/{attempt_id} once submitted"""

    user: User
    title: str
    passage_id: int
    content: AttemptContent
    attempt: Attempt
    answers: dict[int, int]
