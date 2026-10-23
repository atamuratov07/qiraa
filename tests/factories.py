"""
Id scheme, so tests can be read without looking anything up:
    question 1 has options 11, 12, 13
    question 2 has options 21, 22, 23
    question N has options N1, N2, N3, and `correct` picks which one is right
"""

from datetime import UTC, datetime

from app.auth.models import User
from app.passages.models import Passage, PassageOption, PassageQuestion

T0 = datetime(2026, 10, 7, 10, 0, 0, tzinfo=UTC)


def make_question(
    question_id: int, *, correct: int, position: int = 1
) -> PassageQuestion:
    return PassageQuestion(
        id=question_id,
        position=position,
        prompt=f"سؤال {question_id}؟",
        explanation=f"Explanation for question {question_id}",
        options=[
            PassageOption(
                id=question_id * 10 + k,
                position=k,
                text=f"خيار {k}",
                is_correct=(k == correct),
            )
            for k in (1, 2, 3)
        ],
    )


def make_passage(
    passage_id: int,
    questions: list[PassageQuestion],
    *,
    level: str = "A2",
    owner: User | None = None,
    is_common: bool | None = None,
) -> Passage:
    for position, question in enumerate(questions, start=1):
        question.position = position
    return Passage(
        id=passage_id,
        slug=f"passage-{passage_id}",
        title=f"نص {passage_id}",
        level=level,
        text="الفقرة الأولى.\n\nالفقرة الثانية.",
        owner_id=owner.id if owner else None,
        is_common=owner is None if is_common is None else is_common,
        translation_ru=None,
        questions=questions,
    )


def make_user(user_id: int, username: str, *, is_admin: bool = False) -> User:
    return User(
        id=user_id,
        username=username,
        password_hash="not-a-real-hash",
        created_at=T0,
        is_admin=is_admin,
    )
