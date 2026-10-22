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


def empty_to_none(value: str | None) -> str | None:
    return value or None


LETTERS = "ABCDEF"
MIN_OPTIONS = 2
MAX_OPTIONS = len(LETTERS)
MAX_TITLE = 200
MAX_LEVEL = 16

NonEmpty = Annotated[str, StringConstraints(min_length=1)]
Title = Annotated[str, StringConstraints(max_length=MAX_TITLE)]


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


class PassageIn(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", str_strip_whitespace=True
    )

    title: Annotated[Title | None, AfterValidator(empty_to_none)] = None
    level: Annotated[str, StringConstraints(max_length=MAX_LEVEL)] = ""
    text: NonEmpty
    translation_ru: Annotated[str | None, AfterValidator(empty_to_none)] = None
    glossary: dict[NonEmpty, NonEmpty] = Field(default_factory=dict)
    questions: Annotated[list[QuestionIn], Field(min_length=1)]
