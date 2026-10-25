from datetime import UTC, datetime
from http import HTTPStatus
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import models  # noqa: F401  registers every model before the first query
from app.auth.deps import LoginRequired
from app.auth.models import User
from app.auth.routes import router as auth_router
from app.content.routes import router as content_router
from app.core.config import APP_DIR
from app.core.i18n import N_, LocaleMiddleware, _
from app.core.redirects import return_path
from app.core.templating import render, templates
from app.core.timeutils import local_day
from app.core.views import ErrorPage
from app.grammar.routes import router as grammar_router
from app.passages.routes import router as passages_router
from app.practice.api import router as api_router
from app.practice.routes import router as practice_router
from app.profile.routes import router as profile_router
from app.profile.streaks import visible_streak


def streak_today(user: User) -> int:
    return visible_streak(user, local_day(datetime.now(UTC)))


templates.env.globals["streak_today"] = streak_today  # pyright: ignore[reportArgumentType]

app = FastAPI(title="Qiraa")
app.add_middleware(LocaleMiddleware)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

for router in (
    auth_router,
    grammar_router,
    passages_router,
    practice_router,
    api_router,
    profile_router,
    content_router,
):
    app.include_router(router)


@app.get("/")
def home() -> RedirectResponse:
    return RedirectResponse("/passages", status_code=303)


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


def _is_api(request: Request) -> bool:
    return request.url.path.startswith("/api/")


# Starlette's own errors (unknown URL, wrong method) carry the English status phrase,
# which is then the msgid. Listed here only so that pybabel extracts them.
STATUS_PHRASES = (
    N_("Bad Request"),
    N_("Unauthorized"),
    N_("Forbidden"),
    N_("Not Found"),
    N_("Method Not Allowed"),
    N_("Conflict"),
    N_("Internal Server Error"),
)


def _error_page(request: Request, status_code: int, message: str) -> Response:
    ctx: ErrorPage = {"user": None, "status_code": status_code, "message": message}
    return render(request, "error.html", ctx, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
    if _is_api(request):
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    message = str(exc.detail)
    if message == HTTPStatus(exc.status_code).phrase:
        message = _(message)

    return _error_page(request, exc.status_code, message)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError) -> Response:
    if _is_api(request):
        return await request_validation_exception_handler(request, exc)

    return _error_page(request, 404, _("Not Found"))


@app.exception_handler(LoginRequired)
async def login_required(request: Request, _exc: LoginRequired) -> Response:
    if _is_api(request):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)

    target = return_path(request)
    next_query = "" if target == "/" else f"?next={quote(target, safe='/')}"
    return RedirectResponse(f"/login{next_query}", status_code=303)
