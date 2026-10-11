from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base

if TYPE_CHECKING:
    from app.practice.models import Attempt, Question


class Passage(Base):
    __tablename__: str = "passages"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
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
