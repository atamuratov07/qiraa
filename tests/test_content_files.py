"""Every content file in the repo parses, so a broken one fails CI before anyone imports it."""

from pathlib import Path

import pytest

from app.content.errors import ContentError, describe
from app.content.loader import parse_file
from app.core.config import BASE_DIR

FILES = sorted((BASE_DIR / "content").glob("*.yaml"))


def test_there_are_content_files() -> None:
    assert FILES


@pytest.mark.parametrize("path", FILES, ids=[path.name for path in FILES])
def test_content_file_is_valid(path: Path) -> None:
    try:
        parse_file(path.read_text(encoding="utf-8"))
    except ContentError as e:
        pytest.fail(
            "\n".join(f"{path.name}:{err.line}: {describe(err)}" for err in e.errors)
        )
