from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.passages.models import Passage
from app.practice.models import Attempt, Option


@dataclass(frozen=True, slots=True)
class QuestionView:
    id: int
    prompt: str
    explanation: str | None
    options: list[Option]


class AttemptPage(TypedDict):
    """practice/attempt.html, GET /attempts/{attempt_id} while the attempt is open"""

    user: User
    passage: Passage
    attempt: Attempt
    questions: list[QuestionView]
    answers: dict[int, int]
    paused: bool


class ResultPage(TypedDict):
    """practice/result.html, GET /attempts/{attempt_id} once submitted"""

    user: User
    passage: Passage
    attempt: Attempt
    questions: list[QuestionView]
    answers: dict[int, int]
