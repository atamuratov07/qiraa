from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.deps import LoginRequired
from app.routers import auth, passages

app = FastAPI(title="Qiraa")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")


for r in (auth.router, passages.router):
    app.include_router(r)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.exception_handler(LoginRequired)
def _login_required(request: Request, _exc: LoginRequired):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not logged in"}, status_code=401)

    target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    next = "" if target == "/" else f"?next={quote(target, safe='/')}"
    return RedirectResponse(f"/login{next}", status_code=303)
