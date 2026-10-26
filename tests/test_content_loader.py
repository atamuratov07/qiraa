"""Level 1: reading content files, with no database. Line numbers in the files are 1-based."""

import pytest

from app.content.errors import ContentError, LineError, describe
from app.content.loader import parse
from app.core.i18n import use_locale
from app.passages.schemas import PassageFile

VALID = """\
passages:
  - slug: b1-media
    title: ""
    level: B1
    text: |
      الفقرة الأولى.

      الفقرة الثانية.
    questions:
      - prompt: سؤال؟
        options: [أ, ب, ج]
        answer: C
        explanation:
"""


def errors(text: str) -> list[LineError]:
    with pytest.raises(ContentError) as raised:
        parse(text, PassageFile)
    return raised.value.errors


def where(text: str) -> list[tuple[int | None, str, str]]:
    return [(e.line, e.path, e.type) for e in errors(text)]


def test_a_valid_file() -> None:
    passage = parse(VALID, PassageFile).passages[0]

    assert (passage.slug, passage.title) == ("b1-media", None)
    assert passage.text == "الفقرة الأولى.\n\nالفقرة الثانية."  # | keeps the blank line
    assert passage.questions[0].correct_index == 2
    assert passage.questions[0].explanation is None


def test_errors_point_at_their_lines_in_file_order() -> None:
    text = """\
passages:
  - text: نص
    questions:
      - prompt: سؤال؟
        options: [أ, ب]
        answer: D
      - options:
          - أ
          - 2010
        answer: B
        skil: detail
    slug: Bad Slug
"""
    assert where(text) == [
        (6, "passages[0].questions[0].answer", "answer_out_of_range"),
        (7, "passages[0].questions[1].prompt", "missing"),  # the block without it
        (9, "passages[0].questions[1].options[1]", "string_type"),
        (11, "passages[0].questions[1].skil", "extra_forbidden"),
        (12, "passages[0].slug", "bad_slug"),
    ]


def test_a_syntax_error_has_its_line() -> None:
    [error] = errors("passages:\n  - slug: a\n   text: b\n")

    assert (error.line, error.type) == (3, "yaml_syntax")
    assert "expected <block end>" in describe(error)


def test_aliases_are_refused_before_they_expand() -> None:
    text = """\
passages:
  - slug: a
    text: &t نص
    questions: [{prompt: *t, options: [*t, ب], answer: A}]
"""
    assert where(text) == [(3, "", "yaml_alias")]


def test_a_repeated_key_is_an_error() -> None:
    text = "passages:\n  - slug: a\n    text: نص\n    text: نص آخر\n"

    assert where(text) == [(4, "passages[0].text", "duplicate_key")]


@pytest.mark.parametrize(
    ("text", "line", "type"),
    [
        ("# only a comment\n", None, "empty"),
        ("- a\n- b\n", 1, "model_type"),
        ("[" * 500 + "]" * 500, 1, "too_deep"),  # would overflow PyYAML's recursion
        ("passages:\n  - text: a\x0bb\n", 2, "bad_character"),  # Word's line break
    ],
    ids=["empty", "list", "deep", "control character"],
)
def test_files_that_are_not_content(text: str, line: int | None, type: str) -> None:
    [error] = errors(text)

    assert (error.line, error.type) == (line, type)


def test_messages_are_translated_when_shown() -> None:
    [error] = errors(VALID.replace("answer: C", "answer: D"))

    with use_locale("en"):
        english = describe(error)
    with use_locale("ru"):
        russian = describe(error)

    assert english == "Answer D is out of range: this question has 3 options."
    assert russian == "Ответа D нет: вариантов в этом вопросе всего 3."
