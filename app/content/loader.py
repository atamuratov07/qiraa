from typing import cast

from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails
from yaml.nodes import Node

from app.content.errors import ContentError, LineError, to_line_error
from app.content.yaml_tree import line_of, read_yaml
from app.grammar.schemas import GrammarFile
from app.passages.schemas import PassageFile

MAX_BYTES = 1024 * 1024


def decode(raw: bytes) -> str:
    """Text of an uploaded file. Reading MAX_BYTES + 1 bytes is enough to refuse a larger
    one. utf-8-sig drops the byte order mark some Windows editors add."""
    if len(raw) > MAX_BYTES:
        too_large = LineError(
            None, "", "file_too_large", "The file is too large", {"limit": "1 MB"}
        )
        raise ContentError([too_large])

    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        not_utf8 = LineError(None, "", "not_utf8", "The file is not UTF-8", {})
        raise ContentError([not_utf8]) from e


def validate[F: BaseModel](root: Node, data: object, schema: type[F]) -> F:
    try:
        return schema.model_validate(data)

    except ValidationError as e:
        errors = [from_pydantic(root, error) for error in e.errors(include_url=False)]
        errors.sort(key=lambda error: error.line or 0)

        raise ContentError(errors) from e


def parse[F: BaseModel](text: str, schema: type[F]) -> F:
    return validate(*read_yaml(text), schema)


def parse_file(text: str) -> PassageFile | GrammarFile:
    """A file of either kind, told apart by its top key. A file with both keys is read
    as a passages file, which reports `grammar` as an unknown field."""
    root, data = read_yaml(text)
    keys = top_keys(data)
    grammar = "grammar" in keys and "passages" not in keys

    return validate(root, data, GrammarFile if grammar else PassageFile)


def top_keys(data: object) -> set[object]:
    return set(cast(dict[object, object], data)) if isinstance(data, dict) else set()


def from_pydantic(root: Node, error: ErrorDetails) -> LineError:
    return to_line_error(error, line_of(root, error["loc"]))
