from __future__ import annotations

from sqlalchemy import (
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


class GrammarQuestion(Owned, Base):
    __tablename__: str = "grammar_questions"
    __table_args__: tuple[CheckConstraint, Index, Index] = (
        common_or_owned(),
        unique_where(
            "uq_grammar_questions_slug_common", "slug", where=column("is_common")
        ),
        unique_where(
            "uq_grammar_questions_owner_slug_private",
            "owner_id",
            "slug",
            where=not_(column("is_common")),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str | None] = mapped_column(String(80))
    prompt: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)

    options: Mapped[list[GrammarOption]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="GrammarOption.position",
        passive_deletes=True,
    )


class GrammarOption(Base):
    __tablename__: str = "grammar_options"
    __table_args__: tuple[UniqueConstraint, Index] = (
        UniqueConstraint("question_id", "position"),
        unique_where(
            "uq_grammar_options_one_correct",
            "question_id",
            where=column("is_correct"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("grammar_questions.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(default=False)

    question: Mapped[GrammarQuestion] = relationship(back_populates="options")
