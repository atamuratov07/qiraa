from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.deps import LoginRequired
from app.routers import api, attempts, auth, passages, profile
from app.templating import APP_DIR, render
from app.views import ErrorPage

app = FastAPI(title="Qiraa")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

for router in (
    auth.router,
    passages.router,
    attempts.router,
    api.router,
    profile.router,
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


def _error_page(request: Request, status_code: int, message: str) -> Response:
    ctx: ErrorPage = {"user": None, "status_code": status_code, "message": message}
    return render(request, "error.html", ctx, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
    if _is_api(request):
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )

    return _error_page(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError) -> Response:
    if _is_api(request):
        return await request_validation_exception_handler(request, exc)

    return _error_page(request, 404, "Page not found")


@app.exception_handler(LoginRequired)
async def login_required(request: Request, _exc: LoginRequired) -> Response:
    if _is_api(request):
        return JSONResponse({"detail": "Not logged in"}, status_code=401)

    target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    next_query = "" if target == "/" else f"?next={quote(target, safe='/')}"
    return RedirectResponse(f"/login{next_query}", status_code=303)
