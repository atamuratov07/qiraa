"""Level 1: the checks the content schemas add to Pydantic's own."""

import pytest
from pydantic import BaseModel, ValidationError

from app.content.schemas import QuestionIn
from app.passages.schemas import PassageEntry, PassageFile, PassageIn

QUESTION = {"prompt": "سؤال؟", "options": ["أ", "ب", "ج"], "answer": "B"}
PASSAGE = {"slug": "b1-media", "text": "الفقرة.", "questions": [QUESTION]}


def error_types(model: type[BaseModel], data: object) -> list[str]:
    with pytest.raises(ValidationError) as raised:
        model.model_validate(data)
    return [e["type"] for e in raised.value.errors()]


@pytest.mark.parametrize("empty", ["", None])
def test_empty_optional_text_becomes_none(empty: str | None) -> None:
    passage = PassageIn.model_validate(
        {
            "title": empty,
            "translation_ru": empty,
            "text": "الفقرة.",
            "questions": [{**QUESTION, "explanation": empty}],
        }
    )

    assert (passage.title, passage.translation_ru) == (None, None)
    assert passage.questions[0].explanation is None


@pytest.mark.parametrize(
    ("answer", "type"),
    [("b", "bad_answer"), (2, "bad_answer"), ("D", "answer_out_of_range")],
)
def test_the_answer_is_the_letter_of_an_option(answer: object, type: str) -> None:
    assert error_types(QuestionIn, {**QUESTION, "answer": answer}) == [type]


def test_options_are_different() -> None:
    data = {**QUESTION, "options": ["أ", "ب", "أ"]}

    assert error_types(QuestionIn, data) == ["duplicate_option"]


@pytest.mark.parametrize("slug", ["B1-media", "b1--media"])
def test_a_slug_is_lowercase_words_with_hyphens(slug: str) -> None:
    assert error_types(PassageEntry, {**PASSAGE, "slug": slug}) == ["bad_slug"]


def test_slugs_are_unique_in_a_file() -> None:
    data = {"passages": [PASSAGE, {**PASSAGE, "text": "نص آخر."}]}

    assert error_types(PassageFile, data) == ["duplicate_slug"]
