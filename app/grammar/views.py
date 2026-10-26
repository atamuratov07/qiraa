from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.content.schemas import MAX_OPTIONS, MIN_OPTIONS
from app.practice.views import UnfinishedInfo


@dataclass(frozen=True, slots=True)
class PoolCounts:
    all: int
    mine: int


@dataclass(frozen=True, slots=True)
class ManagedQuestion:
    id: int
    prompt: str
    slug: str | None
    is_common: bool


class GrammarPage(TypedDict):
    """grammar/start.html, GET /grammar (and POST /grammar/sessions on an empty pool)"""

    user: User
    counts: PoolCounts
    unfinished: UnfinishedInfo | None
    empty_pool: bool


class ManagePage(TypedDict):
    """grammar/manage.html, GET /manage/grammar"""

    user: User
    questions: list[ManagedQuestion]


class EditorLimits(TypedDict):
    min_options: int
    max_options: int


EDITOR_LIMITS: EditorLimits = {
    "min_options": MIN_OPTIONS,
    "max_options": MAX_OPTIONS,
}


class EditorPage(TypedDict):
    """grammar/editor.html, GET and POST /manage/grammar/new and /{id}/edit"""

    user: User
    question_id: int | None
    slug: str | None
    common: bool
    data: dict[str, object] | None
    errors: dict[str, str]
    limits: EditorLimits
