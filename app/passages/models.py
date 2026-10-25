from __future__ import annotations

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    column,
    not_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, Owned, common_or_owned, unique_where
from app.core.text import display_title


class Passage(Owned, Base):
    __tablename__: str = "passages"
    __table_args__: tuple[CheckConstraint, Index, Index] = (
        common_or_owned(),
        unique_where("uq_passages_slug_common", "slug", where=column("is_common")),
        unique_where(
            "uq_passages_owner_slug_private",
            "owner_id",
            "slug",
            where=not_(column("is_common")),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(16), default="")
    text: Mapped[str] = mapped_column(Text)
    translation_ru: Mapped[str | None] = mapped_column(Text)
    glossary: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    questions: Mapped[list[PassageQuestion]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        order_by="PassageQuestion.position",
        passive_deletes=True,
    )

    @property
    def display_title(self) -> str:
        return display_title(self.title, self.text)


class PassageQuestion(Base):
    __tablename__: str = "passage_questions"
    __table_args__: tuple[UniqueConstraint, ...] = (
        UniqueConstraint("passage_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    passage_id: Mapped[int] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column()
    prompt: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)

    passage: Mapped[Passage] = relationship(back_populates="questions")

    options: Mapped[list[PassageOption]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="PassageOption.position",
        passive_deletes=True,
    )


class PassageOption(Base):
    __tablename__: str = "passage_options"
    __table_args__: tuple[UniqueConstraint, Index] = (
        UniqueConstraint("question_id", "position"),
        unique_where(
            "uq_passage_options_one_correct",
            "question_id",
            where=column("is_correct"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("passage_questions.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(default=False)

    question: Mapped[PassageQuestion] = relationship(back_populates="options")
