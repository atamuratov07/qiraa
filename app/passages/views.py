from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.passages.models import Passage


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
class ManagedPassage:
    id: int
    title: str
    level: str
    slug: str | None
    is_common: bool
    question_count: int


class PassagesPage(TypedDict):
    """passages/list.html, GET /passages"""

    user: User
    streak: int
    passages: list[PassageCard]


class PassageStartPage(TypedDict):
    """passages/start.html, GET /passages/{passage_id} when there is no open attempt"""

    user: User
    passage: Passage
    question_count: int
    best: int | None
    tries: int
