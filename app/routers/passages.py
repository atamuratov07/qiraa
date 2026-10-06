from fastapi import APIRouter, HTTPException, Request

from app.templating import templates

router = APIRouter(tags=["passages"])


@router.get("/passages")
def passages(request: Request):
    return templates.TemplateResponse(
        request,
        "passages.html",
        {
            "user": {"username": "damir"},
            "streak": 0,
            "passages": [{"id": 1, "title": "في السوق", "level": "A2"}],
        },
    )


@router.get("/passages/{pid}")
def passage(request: Request, pid: int):
    if pid < 0 or pid > 100:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        request,
        "passage_start.html",
        {
            "user": {"username": "damir"},
            "streak": 0,
            "passage": {"id": pid, "title": "في السوق", "level": "A2"},
            "question_count": 1,
            "best": 15,
            "tries": 3,
        },
    )
