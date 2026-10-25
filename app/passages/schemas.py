from typing import Annotated, ClassVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.content.schemas import (
    NonEmpty,
    QuestionIn,
    WithSlug,
    empty_to_none,
    slugs_are_distinct,
)

MAX_TITLE = 200
MAX_LEVEL = 16

Title = Annotated[str, StringConstraints(max_length=MAX_TITLE)]


class PassageIn(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", str_strip_whitespace=True
    )

    title: Annotated[Title | None, AfterValidator(empty_to_none)] = None
    level: Annotated[str, StringConstraints(max_length=MAX_LEVEL)] = ""
    text: NonEmpty
    translation_ru: Annotated[str | None, AfterValidator(empty_to_none)] = None
    questions: Annotated[list[QuestionIn], Field(min_length=1)]


class PassageEntry(WithSlug, PassageIn):
    pass


class PassageFile(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    passages: Annotated[
        list[PassageEntry], Field(min_length=1), AfterValidator(slugs_are_distinct)
    ]
