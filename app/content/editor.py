import json
from typing import cast

from app.core.i18n import N_

EDITOR_MESSAGES: dict[str, str] = {"bad_answer": N_("Choose the correct option.")}


def posted(raw: str) -> dict[str, object] | None:
    """What was posted, to refill the editor"""
    try:
        value = cast(object, json.loads(raw))
    except ValueError:
        return None

    return cast(dict[str, object], value) if isinstance(value, dict) else None
