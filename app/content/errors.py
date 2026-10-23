from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from app.core.i18n import N_, _

MESSAGES: dict[str, str] = {
    "yaml_syntax": N_("This is not valid YAML: %(problem)s"),
    "bad_character": N_(
        "The invisible character %(code)s is not allowed. Delete it or retype the line."
    ),
    "yaml_alias": N_(
        "Anchors and aliases (& and *) are not allowed. Write the value out in full."
    ),
    "too_deep": N_("The lists and blocks are nested too deeply."),
    "duplicate_key": N_("%(key)s appears twice in the same block."),
    "empty": N_("The file is empty."),
    "model_type": N_("Expected a block of key: value lines."),
    "dict_type": N_("Expected a block of key: value lines."),
    "list_type": N_("Expected a list of items starting with a dash (-)."),
    "missing": N_("The field %(field)s is missing."),
    "extra_forbidden": N_("Unknown field %(field)s. Check the spelling."),
    "string_type": N_(
        "Expected text. Quote a value that looks like a number, a date, yes or no."
    ),
    "string_too_short": N_("This can't be empty."),
    "string_too_long": N_("Too long: the limit is %(max_length)s characters."),
    "too_short": N_("Too few items: at least %(min_length)s are needed."),
    "too_long": N_("Too many items: the limit is %(max_length)s."),
    "bad_answer": N_("The answer must be a letter from A to F."),
    "duplicate_option": N_("The option %(option)s appears twice."),
    "answer_out_of_range": N_(
        "Answer %(answer)s is out of range: this question has %(count)s options."
    ),
    "bad_slug": N_(
        "Use lowercase Latin letters, digits and single hyphens, like b1-media."
    ),
    "duplicate_slug": N_("The slug %(slug)s is used by more than one passage."),
    "import_conflict": N_(
        "Someone imported the same passage at the same moment. Import the file again."
    ),
    "file_too_large": N_("The file is larger than %(limit)s."),
    "not_utf8": N_("The file is not UTF-8 text. Save it as UTF-8 and try again."),
}

type Loc = tuple[int | str, ...]


@dataclass(frozen=True)
class LineError:
    line: int | None  # 1-based
    path: str  # passages[0].questions[2].answer
    type: str
    message: str
    ctx: dict[str, object]


class ContentError(Exception):
    def __init__(self, errors: list[LineError]) -> None:
        super().__init__(f"{len(errors)} error(s) in the content file")
        self.errors: list[LineError] = errors


def format_path(loc: Loc) -> str:
    path = ""
    for part in loc:
        if isinstance(part, int):
            path += f"[{part}]"
        elif part.startswith("["):  # Pydantic's "[key]" for a bad dict key
            path += part
        else:
            path += f".{part}" if path else part
    return path


def to_line_error(error: ErrorDetails, line: int | None) -> LineError:
    loc = error["loc"]
    ctx: dict[str, object] = dict(error.get("ctx", {}))
    if error["type"] in ("missing", "extra_forbidden") and loc:
        ctx["field"] = loc[-1]
    return LineError(line, format_path(loc), error["type"], error["msg"], ctx)


def describe(error: LineError) -> str:
    if error.type not in MESSAGES:
        return error.message
    return _(MESSAGES[error.type], **error.ctx)


def messages_by_path(
    exc: ValidationError, overrides: Mapping[str, str] | None = None
) -> dict[str, str]:
    """The first message for each path; `overrides` replaces a type's wording."""
    messages: dict[str, str] = {}

    for detail in exc.errors():
        e = to_line_error(detail, None)
        if overrides and e.type in overrides:
            message = _(overrides[e.type], **e.ctx)
        else:
            message = describe(e)
        messages.setdefault(e.path, message)

    return messages
