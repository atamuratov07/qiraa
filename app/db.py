from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()
_is_sqlite = settings.sqlalchemy_url.startswith("sqlite")

engine = create_engine(
    settings.sqlalchemy_url,
    # Neon suspends idle databases; pre_ping tests a pooled connection before
    # using it, so a connection killed during a suspend gets replaced silently.
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:
    # SQLite ignores foreign keys (and ON DELETE CASCADE) unless asked per connection.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one DB session per request, always closed afterwards."""
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]
