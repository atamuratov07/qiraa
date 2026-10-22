from dataclasses import dataclass
from typing import TypedDict

from app.auth.models import User
from app.content.service import ImportReport


@dataclass(frozen=True, slots=True)
class ShownError:
    line: int | None
    path: str
    message: str


class ImportPage(TypedDict):
    """content/import.html, GET and POST /manage/import"""

    user: User
    text: str
    common: bool
    errors: list[ShownError]
    report: ImportReport | None
    prompt: str
