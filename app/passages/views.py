from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.passages.models import Passage
from app.passages.schemas import MAX_LEVEL, MAX_OPTIONS, MAX_TITLE, MIN_OPTIONS


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


class ManagePage(TypedDict):
    """passages/manage.html, GET /manage/passages"""

    user: User
    passages: list[ManagedPassage]


class EditorLimits(TypedDict):
    title: int
    level: int
    min_options: int
    max_options: int


EDITOR_LIMITS: EditorLimits = {
    "title": MAX_TITLE,
    "level": MAX_LEVEL,
    "min_options": MIN_OPTIONS,
    "max_options": MAX_OPTIONS,
}


class EditorPage(TypedDict):
    """passages/editor.html, GET and POST /manage/passages/new and /{id}/edit"""

    user: User
    passage_id: int | None
    slug: str | None
    common: bool
    data: dict[str, object] | None
    errors: dict[str, str]
    limits: EditorLimits
