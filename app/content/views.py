from dataclasses import dataclass
from typing import Literal, TypedDict

from app.auth.models import User
from app.content.service import ImportReport

type ImportKind = Literal["passages", "grammar"]


@dataclass(frozen=True, slots=True)
class ShownError:
    line: int | None
    path: str
    message: str


class ImportPage(TypedDict):
    """content/import.html, GET and POST /manage/{passages,grammar}/import"""

    user: User
    kind: ImportKind
    text: str
    common: bool
    errors: list[ShownError]
    report: ImportReport | None
    prompt: str
