from pydantic import ValidationError
from pydantic_core import ErrorDetails
from yaml.nodes import Node

from app.content.errors import ContentError, LineError, format_path
from app.content.schemas import ContentFile
from app.content.yaml_tree import line_of, read_yaml


def parse(text: str) -> ContentFile:
    root, data = read_yaml(text)

    try:
        return ContentFile.model_validate(data)

    except ValidationError as e:
        errors = [from_pydantic(root, error) for error in e.errors(include_url=False)]
        errors.sort(key=lambda error: error.line or 0)

        raise ContentError(errors) from e


def from_pydantic(root: Node, error: ErrorDetails) -> LineError:
    loc = error["loc"]
    ctx: dict[str, object] = dict(error.get("ctx", {}))
    if error["type"] in ("missing", "extra_forbidden") and loc:
        ctx["field"] = loc[-1]
    return LineError(
        line_of(root, loc), format_path(loc), error["type"], error["msg"], ctx
    )
