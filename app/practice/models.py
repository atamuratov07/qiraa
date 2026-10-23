from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal, TypedDict

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    and_,
    column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, unique_where
from app.core.text import display_title

if TYPE_CHECKING:
    from app.auth.models import User

AttemptKind = Literal["passage", "grammar"]


class OptionCopy(TypedDict):
    id: int
    text: str
    is_correct: bool


class QuestionCopy(TypedDict):
    id: int
    prompt: str
    explanation: str | None
    options: list[OptionCopy]


class AttemptContent(TypedDict):
    title: str | None
    level: str
    text: str
    translation_ru: str | None
    questions: list[QuestionCopy]


class Attempt(Base):
    __tablename__: str = "attempts"
    __table_args__: tuple[Index | CheckConstraint, ...] = (
        unique_where(
            "uq_attempts_one_open",
            "user_id",
            "passage_id",
            where=column("submitted_at").is_(None),
        ),
        unique_where(
            "uq_attempts_one_open_grammar",
            "user_id",
            where=and_(column("submitted_at").is_(None), column("kind") == "grammar"),
        ),
        CheckConstraint("kind IN ('passage', 'grammar')", name="known_kind"),
        CheckConstraint(
            "kind = 'passage' OR passage_id IS NULL", name="grammar_has_no_passage"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    passage_id: Mapped[int | None] = mapped_column(
        ForeignKey("passages.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[AttemptKind] = mapped_column(String(16))
    content: Mapped[AttemptContent] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int | None] = mapped_column()
    total: Mapped[int | None] = mapped_column()

    user: Mapped[User] = relationship(back_populates="attempts")

    answers: Mapped[list[AttemptAnswer]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def display_title(self) -> str:
        return display_title(self.content["title"], self.content["text"])


class AttemptAnswer(Base):
    __tablename__: str = "attempt_answers"
    __table_args__: tuple[UniqueConstraint, ...] = (
        UniqueConstraint("attempt_id", "question_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"),
    )
    question_id: Mapped[int] = mapped_column()
    option_id: Mapped[int] = mapped_column()

    attempt: Mapped[Attempt] = relationship(back_populates="answers")
