from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(
    get_settings().sqlalchemy_url,
    # Neon suspends idle databases; pre_ping tests a pooled connection before
    # using it, so a connection killed during a suspend gets replaced silently.
    pool_pre_ping=True,
    pool_recycle=300,
)


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one DB session per request, always closed afterwards."""
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]
