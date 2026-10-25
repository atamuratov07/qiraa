from typing import Annotated, ClassVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.content.schemas import QuestionIn, WithSlug, slugs_are_distinct


class GrammarEntry(WithSlug, QuestionIn):
    pass


class GrammarFile(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    grammar: Annotated[
        list[GrammarEntry], Field(min_length=1), AfterValidator(slugs_are_distinct)
    ]
