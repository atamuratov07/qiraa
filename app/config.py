from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


def to_sqlalchemy_url(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{BASE_DIR / 'dev.db'}"
    migration_database_url: str | None = None

    @property
    def sqlalchemy_url(self) -> str:
        return to_sqlalchemy_url(self.database_url)

    @property
    def migration_url(self) -> str:
        return to_sqlalchemy_url(self.migration_database_url or self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
