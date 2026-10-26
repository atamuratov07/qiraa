from collections.abc import Iterator
from typing import Protocol, cast

import yaml
from yaml.error import MarkedYAMLError
from yaml.events import CollectionEndEvent, CollectionStartEvent, Event, NodeEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.reader import ReaderError

from app.content.errors import ContentError, LineError, Loc, format_path

# A valid file nests 6 levels (file, passages, passage, questions, question, options).
MAX_DEPTH = 20


class Mark(Protocol):
    line: int


def read_yaml(text: str) -> tuple[Node, object]:
    try:
        check_events(text)
        loader = yaml.SafeLoader(text)
        try:
            root = loader.get_single_node()
            data = None if root is None else construct(loader, root)
        finally:
            loader.dispose()
    except yaml.YAMLError as e:
        raise ContentError([from_yaml(text, e)]) from e

    if root is None:
        raise ContentError([LineError(None, "", "empty", "The file is empty", {})])

    duplicates = [
        LineError(
            line(key.start_mark),
            format_path(loc),
            "duplicate_key",
            f"Duplicate key {loc[-1]}",
            {"key": loc[-1]},
        )
        for key, loc in duplicate_keys(root, ())
    ]

    if duplicates:
        raise ContentError(duplicates)

    return root, data


def check_events(text: str) -> None:
    depth = 0
    for event in events(text):
        if isinstance(event, NodeEvent) and event.anchor is not None:
            raise ContentError(
                [
                    LineError(
                        line(event.start_mark),
                        "",
                        "yaml_alias",
                        "Anchors and aliases are not allowed",
                        {},
                    )
                ]
            )

        if isinstance(event, CollectionStartEvent):
            depth += 1
            if depth > MAX_DEPTH:
                raise ContentError(
                    [LineError(line(event.start_mark), "", "too_deep", "Too deep", {})]
                )
        elif isinstance(event, CollectionEndEvent):
            depth -= 1


def duplicate_keys(node: Node, loc: Loc) -> Iterator[tuple[ScalarNode, Loc]]:
    if isinstance(node, MappingNode):
        seen: set[str] = set()
        for key, value in pairs(node):
            if not isinstance(key, ScalarNode):
                continue
            name = scalar(key)
            if name in seen:
                yield key, (*loc, name)
            seen.add(name)
            yield from duplicate_keys(value, (*loc, name))
    elif isinstance(node, SequenceNode):
        for i, item in enumerate(items(node)):
            yield from duplicate_keys(item, (*loc, i))


def line_of(root: Node, loc: Loc) -> int | None:
    node = root
    mark: Mark | None = root.start_mark
    for part in loc:
        if isinstance(node, MappingNode):
            entry = next(
                (
                    (k, v)
                    for k, v in pairs(node)
                    if isinstance(k, ScalarNode) and scalar(k) == part
                ),
                None,
            )
            if entry is None:
                break
            key, node = entry
            mark = key.start_mark
        elif isinstance(node, SequenceNode) and isinstance(part, int):
            children = items(node)
            if part >= len(children):
                break
            node = children[part]
            mark = node.start_mark
        else:
            break

    return line(mark)


def line(mark: Mark | None) -> int | None:
    return None if mark is None else mark.line + 1


def from_yaml(text: str, error: yaml.YAMLError) -> LineError:
    if isinstance(error, ReaderError):
        # Raised before parsing starts; the position counts characters.
        character, position = cast(tuple[int, int], (error.character, error.position))
        code = f"U+{character:04X}"
        return LineError(
            text.count("\n", 0, position) + 1,
            "",
            "bad_character",
            f"Character {code} is not allowed",
            {"code": code},
        )

    if isinstance(error, MarkedYAMLError):
        problem = error.problem or error.context or str(error)
        return LineError(
            line(error.problem_mark), "", "yaml_syntax", problem, {"problem": problem}
        )

    return LineError(None, "", "yaml_syntax", str(error), {"problem": str(error)})


# PyYAML's type stubs leave these untyped.


def events(text: str) -> Iterator[Event]:
    return cast(Iterator[Event], yaml.parse(text, Loader=yaml.SafeLoader))  # pyright: ignore[reportUnknownMemberType]


def construct(loader: yaml.SafeLoader, root: Node) -> object:
    return cast(object, loader.construct_document(root))  # pyright: ignore[reportUnknownMemberType]


def pairs(node: MappingNode) -> list[tuple[Node, Node]]:
    return cast(list[tuple[Node, Node]], node.value)


def items(node: SequenceNode) -> list[Node]:
    return cast(list[Node], node.value)


def scalar(node: ScalarNode) -> str:
    return cast(str, node.value)
