import re
from typing import Annotated, ClassVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)
from pydantic_core import PydanticCustomError

from app.passages.schemas import PassageIn

SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def slug_is_simple(slug: str) -> str:
    if not SLUG.fullmatch(slug):
        raise PydanticCustomError(
            "bad_slug",
            "Slug {slug} is not lowercase Latin words with hyphens",
            {"slug": slug},
        )
    return slug


Slug = Annotated[str, StringConstraints(max_length=80), AfterValidator(slug_is_simple)]


class PassageEntry(PassageIn):
    slug: Slug


class ContentFile(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    passages: Annotated[list[PassageEntry], Field(min_length=1)]

    @field_validator("passages")
    @classmethod
    def slugs_are_distinct(cls, passages: list[PassageEntry]) -> list[PassageEntry]:
        unique_slugs: set[str] = set()

        for p in passages:
            if p.slug in unique_slugs:
                raise PydanticCustomError(
                    "duplicate_slug",
                    "Slug {slug} is used by more than one passage",
                    {"slug": p.slug},
                )

            unique_slugs.add(p.slug)

        return passages
