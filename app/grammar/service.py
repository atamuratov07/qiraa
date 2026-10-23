from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.models import User
from app.content.schemas import QuestionIn
from app.content.service import (
    ImportedItem,
    ImportReport,
    check_importer,
    commit_import,
    slug_scope,
)
from app.grammar.models import GrammarOption, GrammarQuestion
from app.grammar.schemas import GrammarEntry


def build_options(data: QuestionIn) -> list[GrammarOption]:
    return [
        GrammarOption(position=i, text=text, is_correct=(i - 1 == data.correct_index))
        for i, text in enumerate(data.options, start=1)
    ]


def apply_question(db: Session, question: GrammarQuestion, data: QuestionIn) -> None:
    question.prompt = data.prompt
    question.explanation = data.explanation

    if question.options:
        question.options.clear()
        db.flush()

    question.options.extend(build_options(data))


def import_grammar(
    db: Session, entries: list[GrammarEntry], *, owner: User | None, common: bool
) -> ImportReport:
    check_importer(owner, common)

    existing = {
        q.slug: q
        for q in db.scalars(
            select(GrammarQuestion)
            .where(
                slug_scope(GrammarQuestion, owner, common),
                GrammarQuestion.slug.in_([entry.slug for entry in entries]),
            )
            .options(selectinload(GrammarQuestion.options))
        )
    }

    added: list[GrammarQuestion] = []
    updated: list[GrammarQuestion] = []
    for entry in entries:
        question = existing.get(entry.slug)
        if question is not None:
            apply_question(db, question, entry)
            updated.append(question)
        else:
            question = GrammarQuestion(
                slug=entry.slug, owner_id=owner.id if owner else None, is_common=common
            )
            apply_question(db, question, entry)
            db.add(question)
            added.append(question)

    commit_import(db)

    return ImportReport(imported(added), imported(updated))


def imported(questions: list[GrammarQuestion]) -> list[ImportedItem]:
    return [ImportedItem(q.id, q.slug or "", q.prompt) for q in questions]
