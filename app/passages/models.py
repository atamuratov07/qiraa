from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, Index, String, Text, column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Owned, common_or_owned, unique_where

UNTITLED_WORDS = 6

if TYPE_CHECKING:
    from app.practice.models import Attempt, Question


class Passage(Owned, Base):
    __tablename__: str = "passages"
    __table_args__: tuple[CheckConstraint, Index] = (
        common_or_owned(),
        unique_where("uq_passages_slug_common", "slug", where=column("is_common")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(16), default="")
    text: Mapped[str] = mapped_column(Text)
    translation_ru: Mapped[str | None] = mapped_column(Text)
    glossary: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    questions: Mapped[list[Question]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        order_by="Question.position",
        passive_deletes=True,
    )
    attempts: Mapped[list[Attempt]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def display_title(self) -> str:
        """The title, or the first words of the text when there is none."""
        if self.title:
            return self.title
        words = self.text.split()
        if len(words) <= UNTITLED_WORDS:
            return " ".join(words)
        return " ".join(words[:UNTITLED_WORDS]) + "…"
