from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.practice.views import UnfinishedInfo


@dataclass(frozen=True, slots=True)
class PoolCounts:
    all: int
    mine: int


class GrammarPage(TypedDict):
    """grammar/start.html, GET /grammar (and POST /grammar/sessions on an empty pool)"""

    user: User
    counts: PoolCounts
    unfinished: UnfinishedInfo | None
    empty_pool: bool
