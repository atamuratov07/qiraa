from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.routers import passages

app = FastAPI(title="Qiraa")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")


for r in (passages.router,):
    app.include_router(r)


@app.get("/healthz")
def healthz():
    return {"ok": True}
