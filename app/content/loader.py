from pydantic import ValidationError
from pydantic_core import ErrorDetails
from yaml.nodes import Node

from app.content.errors import ContentError, LineError, to_line_error
from app.content.schemas import ContentFile
from app.content.yaml_tree import line_of, read_yaml

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


def parse(text: str) -> ContentFile:
    root, data = read_yaml(text)

    try:
        return ContentFile.model_validate(data)

    except ValidationError as e:
        errors = [from_pydantic(root, error) for error in e.errors(include_url=False)]
        errors.sort(key=lambda error: error.line or 0)

        raise ContentError(errors) from e


def from_pydantic(root: Node, error: ErrorDetails) -> LineError:
    return to_line_error(error, line_of(root, error["loc"]))
