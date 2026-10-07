"""
Id scheme, so tests can be read without looking anything up:
    question 1 has options 11, 12, 13
    question 2 has options 21, 22, 23
    question N has options N1, N2, N3, and `correct` picks which one is right
"""

from datetime import UTC, datetime

from app.models import Option, Passage, Question, User

T0 = datetime(2026, 10, 7, 10, 0, 0, tzinfo=UTC)


def make_question(question_id: int, *, correct: int, position: int = 1) -> Question:
    return Question(
        id=question_id,
        position=position,
        prompt=f"سؤال {question_id}؟",
        explanation=f"Explanation for question {question_id}",
        options=[
            Option(
                id=question_id * 10 + k,
                position=k,
                text=f"خيار {k}",
                is_correct=(k == correct),
            )
            for k in (1, 2, 3)
        ],
    )


def make_passage(
    passage_id: int, questions: list[Question], *, level: str = "A2"
) -> Passage:
    for position, question in enumerate(questions, start=1):
        question.position = position
    return Passage(
        id=passage_id,
        slug=f"passage-{passage_id}",
        title=f"نص {passage_id}",
        level=level,
        text="الفقرة الأولى.\n\nالفقرة الثانية.",
        translation_ru=None,
        questions=questions,
    )


def make_user(user_id: int, username: str) -> User:
    return User(
        id=user_id, username=username, password_hash="not-a-real-hash", created_at=T0
    )
