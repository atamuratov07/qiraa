from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import DB
from app.deps import CurrentUser
from app.models import Passage, Question
from app.templating import templates

router = APIRouter(tags=["passages"])


@router.get("/passages")
def passages(request: Request, db: DB, user: CurrentUser):
    passages = db.scalars(select(Passage).order_by(Passage.level, Passage.title)).all()

    return templates.TemplateResponse(
        request,
        "passages.html",
        {
            "user": user,
            "streak": 0,
            "passages": passages,
        },
    )


@router.get("/passages/{pid}")
def passage(request: Request, pid: int, db: DB, user: CurrentUser):
    passage = db.scalar(
        select(Passage)
        .where(Passage.id == pid)
        .options(selectinload(Passage.questions).selectinload(Question.options))
    )
    if passage is None:
        raise HTTPException(404, "Passage not found")

    return templates.TemplateResponse(
        request,
        "passage_start.html",
        {
            "user": user,
            "streak": 0,
            "passage": passage,
            "question_count": len(passage.questions),
        },
    )
