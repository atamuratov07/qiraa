from datetime import UTC, date, datetime
from typing import ClassVar

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ColumnElement,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def unique_where(name: str, *columns: str, where: ColumnElement[bool]) -> Index:
    return Index(
        name, *columns, unique=True, postgresql_where=where, sqlite_where=where
    )


class Base(DeclarativeBase):
    metadata: ClassVar[MetaData] = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class User(Base):
    __tablename__: str = "users"
    __table_args__: tuple[CheckConstraint, ...] = (
        CheckConstraint("username = lower(username)", name="username_lowercase"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    current_streak: Mapped[int] = mapped_column(Integer, server_default="0")
    longest_streak: Mapped[int] = mapped_column(Integer, server_default="0")
    last_active_on: Mapped[date | None] = mapped_column(Date)

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserSession(Base):
    __tablename__: str = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class Passage(Base):
    __tablename__: str = "passages"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(16), default="")
    text: Mapped[str] = mapped_column(Text)
    translation_ru: Mapped[str | None] = mapped_column(Text)
    glossary: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        order_by="Question.position",
        passive_deletes=True,
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Question(Base):
    __tablename__: str = "questions"
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

    options: Mapped[list["Option"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Option.position",
        passive_deletes=True,
    )


class Option(Base):
    __tablename__: str = "options"
    __table_args__: tuple[UniqueConstraint, Index] = (
        UniqueConstraint("question_id", "position"),
        unique_where(
            "uq_options_one_correct",
            "question_id",
            where=column("is_correct"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(default=False)

    question: Mapped[Question] = relationship(back_populates="options")


class Attempt(Base):
    __tablename__: str = "attempts"
    __table_args__: tuple[Index, ...] = (
        unique_where(
            "uq_attempts_one_open",
            "user_id",
            "passage_id",
            where=column("submitted_at").is_(None),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    passage_id: Mapped[int] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE"), index=True
    )
    option_order: Mapped[dict[str, list[int]]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int | None] = mapped_column()
    total: Mapped[int | None] = mapped_column()

    user: Mapped[User] = relationship(back_populates="attempts")
    passage: Mapped[Passage] = relationship(back_populates="attempts")

    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AttemptAnswer(Base):
    __tablename__: str = "attempt_answers"
    __table_args__: tuple[UniqueConstraint, ...] = (
        UniqueConstraint("attempt_id", "question_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"),
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    option_id: Mapped[int] = mapped_column(
        ForeignKey("options.id", ondelete="CASCADE"), index=True
    )

    attempt: Mapped[Attempt] = relationship(back_populates="answers")
