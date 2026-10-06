from typing import ClassVar

from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    column,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


class Passage(Base):
    __tablename__: str = "passages"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(String(16), default="")
    text: Mapped[str] = mapped_column(Text)
    translation_ru: Mapped[str | None] = mapped_column(Text, default=None)
    glossary: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="passage",
        cascade="all, delete-orphan",
        order_by="Question.position",
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
    explanation: Mapped[str | None] = mapped_column(Text, default=None)

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
        Index(
            "uq_options_one_correct_per_question",
            "question_id",
            unique=True,
            postgresql_where=column("is_correct"),
            sqlite_where=column("is_correct"),
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
