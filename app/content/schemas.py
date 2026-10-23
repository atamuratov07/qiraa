import re
from typing import Annotated, ClassVar, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError

LETTERS = "ABCDEF"
MIN_OPTIONS = 2
MAX_OPTIONS = len(LETTERS)
SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
MAX_SLUG = 80


def empty_to_none(value: str | None) -> str | None:
    return value or None


NonEmpty = Annotated[str, StringConstraints(min_length=1)]


class QuestionIn(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", str_strip_whitespace=True
    )

    prompt: NonEmpty
    options: Annotated[
        list[NonEmpty], Field(min_length=MIN_OPTIONS, max_length=MAX_OPTIONS)
    ]
    answer: Literal["A", "B", "C", "D", "E", "F"]
    explanation: Annotated[str | None, AfterValidator(empty_to_none)] = None

    @field_validator("options")
    @classmethod
    def options_are_distinct(cls, options: list[str]) -> list[str]:
        unique: set[str] = set()
        for o in options:
            if o in unique:
                raise PydanticCustomError(
                    "duplicate_option", "Option {option} appears twice", {"option": o}
                )
            unique.add(o)

        return options

    @field_validator("answer", mode="before")
    @classmethod
    def answer_is_a_letter(cls, answer: object) -> object:
        if not isinstance(answer, str) or answer.strip() not in tuple(LETTERS):
            raise PydanticCustomError(
                "bad_answer", "Answer must be a letter from A to F"
            )
        return answer.strip()

    @field_validator("answer")
    @classmethod
    def answer_is_an_option(cls, answer: str, info: ValidationInfo) -> str:
        options: list[str] | None = info.data.get("options")
        if options is not None and LETTERS.index(answer) >= len(options):
            raise PydanticCustomError(
                "answer_out_of_range",
                "Answer {answer} is not one of the {count} options",
                {"answer": answer, "count": len(options)},
            )

        return answer

    @property
    def correct_index(self) -> int:
        return LETTERS.index(self.answer)


def slug_is_simple(slug: str) -> str:
    if not SLUG.fullmatch(slug):
        raise PydanticCustomError(
            "bad_slug",
            "Slug {slug} is not lowercase Latin words with hyphens",
            {"slug": slug},
        )
    return slug


Slug = Annotated[
    str, StringConstraints(max_length=MAX_SLUG), AfterValidator(slug_is_simple)
]


class WithSlug(BaseModel):
    slug: Slug


def slugs_are_distinct[E: WithSlug](entries: list[E]) -> list[E]:
    unique: set[str] = set()

    for e in entries:
        if e.slug in unique:
            raise PydanticCustomError(
                "duplicate_slug",
                "Slug {slug} is used twice in this file",
                {"slug": e.slug},
            )
        unique.add(e.slug)

    return entries
