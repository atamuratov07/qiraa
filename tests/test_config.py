from pathlib import Path

import pytest

from app.core.config import BASE_DIR, Settings


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    _ = path.write_text(text)
    return path


def test_env_file_is_read_and_unknown_keys_are_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env = write_env(
        tmp_path, "DATABASE_URL=postgresql://a:b@host/db\nADMIN_USERNAMES=\n"
    )

    settings = Settings(_env_file=env)

    assert settings.sqlalchemy_url == "postgresql+psycopg://a:b@host/db"


def test_environment_variable_beats_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://a:b@host/other")
    env = write_env(tmp_path, "DATABASE_URL=postgresql://a:b@host/db\n")

    assert (
        Settings(_env_file=env).sqlalchemy_url == "postgresql+psycopg://a:b@host/other"
    )


def test_base_dir_is_the_project_root() -> None:
    assert (BASE_DIR / "pyproject.toml").is_file()
