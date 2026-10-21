# Conventions

How the code in this repo is organised and the rules it follows. The plan for the next version
is in [ROADMAP-v2.md](ROADMAP-v2.md); the user-facing description is in
[README.md](../README.md); history is in [CHANGELOG.md](../CHANGELOG.md).

## Stack and hosting

Python 3.13 · FastAPI with Jinja2 server-rendered pages · SQLAlchemy 2.1 · Alembic · Babel ·
Pydantic v2 + pydantic-settings · argon2-cffi · uv · pytest · Tailwind v4 browser build from a
CDN · plain JavaScript (`reader.js`, `attempt.js`, `forms.js`), no build step.

- Production: Docker image on Render (free web service, Frankfurt), Postgres on Neon (free,
  Frankfurt). Every push to `main` deploys. The container runs `alembic upgrade head` on start.
- Local: Postgres 18 from `docker-compose.yml`, with `qiraa` for the app and `qiraa_test` for
  tests. The app runs on the machine. Settings come from the environment, then `.env`.
- CI: `.github/workflows/tests.yml` on every push: `alembic upgrade head`, `alembic check`,
  `alembic downgrade base`, then the tests, all on Postgres 18.

## Commands

```bash
docker compose up -d --wait db
uv sync
uv run alembic upgrade head
uv run python -m app.cli import content/<file>.yaml --owner <username>   # adds or updates by slug
uv run python -m app.cli check content/<file>.yaml                       # no database needed
uv run python -m app.cli make-admin <username>   # prefix DATABASE_URL=... for Neon
uv run fastapi dev app/main.py
uv run pytest                             # on qiraa_test; tables recreated per test
uv run alembic revision --autogenerate -m "..."   # read the file before upgrading
uv run alembic check                      # models and migrations agree
uv run pybabel extract -F babel.cfg --project=Qiraa --version=2.0.0 --width=88 -o app/locale/messages.pot .
uv run pybabel update -i app/locale/messages.pot -d app/locale --width=88 --ignore-obsolete
docker compose down -v                    # delete the local databases
```

`TEST_DATABASE_URL` (`postgresql+psycopg://...`) points the tests elsewhere. It must be a
throwaway database: every test drops all tables.

## Code layout

Organised by feature. `app/main.py` creates the app, includes every router and handles errors.
`app/models.py` imports every model. `content/` holds YAML content files; only
`example.yaml` is in git, so real passages stay private and local. `app/cli.py` holds
commands for running the site (`make-admin`, `import`, `check`). `app/locale/` holds the
`.po` catalogs, read at startup (no compiled `.mo` files).

- `core/`: `base.py` `Base`, `utcnow()`, `unique_where()`, `Owned`, `common_or_owned()` ·
  `config.py` settings, `BASE_DIR`, `APP_DIR` · `permissions.py` `visible()`, `editable()`,
  `load_visible()`, `load_editable()` · `db.py` engine, `get_db`, `DB` alias · `deps.py`
  `FormFields` · `i18n.py` `_()`, `ngettext()`, `N_()`, `use_locale()`, `LocaleMiddleware` ·
  `templating.py` Jinja, `render()`, `local_date` filter · `timeutils.py` `as_utc()`,
  `local_day()` · `redirects.py` `safe_next()`, `return_path()` · `text.py`
  `display_title()` · `views.py` `ErrorPage`.
- `auth/`: `User`, `UserSession` · `deps.py` `CurrentUser`, `MaybeUser`, `LoginRequired` ·
  `security.py` password hashing, session tokens.
- `passages/`: `Passage` · passage list statistics, start card.
- `practice/`: `Question`, `Option`, `Attempt`, `AttemptAnswer`, and the copy an attempt
  keeps (`AttemptContent`, `QuestionCopy`, `OptionCopy`) · attempt service (`copy_passage()`,
  `has_option()`, `grade()`) · pages, `api.py` and `schemas.py` for the JSON endpoints.
- `profile/`: `streaks.py` · profile statistics and page.

A feature has `models.py`, `service.py`, `routes.py` and `views.py` (dataclasses and one
`TypedDict` per page) where it needs them. Templates are in `app/templates/<feature>/`; shared
ones (`base.html`, `error.html`, `_macros.html`, `_popover.html`, `_language_menu.html`) stay
at the top.
`migrations/versions/6ad753184ecc_initial_schema.py` is the single initial schema.

## Rules

1. **Routes stay thin.** Read the request, call a service, choose the response. Services never
   import FastAPI.
2. **Pass `now` in.** Service functions take `now: datetime` (UTC) instead of reading the clock.
3. **Pages render through `render()` with a `TypedDict` context from the feature's
   `views.py`.** Jinja uses
   `StrictUndefined`; every key is required, optional values are `X | None` passed as `None`.
4. **Load owned rows through helpers that check ownership** (`load_attempt(db, user, id)`
   returns `None` for other users' rows). Someone else's object answers 404, never 403. An
   action that conflicts with state (changing a submitted attempt) answers 409.
5. **`/api/*` answers JSON** (`{"detail": ...}`, 401 when logged out); pages redirect to
   `/login` or render `error.html`.
6. **Redirect targets from users go through `safe_next()`.**
7. **The database enforces invariants** (partial unique indexes for one open attempt per
   passage and one correct option per question; unique constraints for upserts). Catch
   `IntegrityError`, `db.rollback()`, and recover; don't rely on check-then-insert alone.
8. **One commit per service write**, at the end, so related changes save together.
9. **Times are UTC in the database** (`DateTime(timezone=True)`). Compare through `as_utc()`,
   which treats a naive datetime as UTC. Dates shown to people or used for streaks go through `local_day()`
   (`APP_TIMEZONE`, default Asia/Tashkent).
10. **Migrations:** a new non-null column on an existing table needs `server_default`. Never
    edit a migration that has run on Neon. Read every autogenerated file (renames come out as
    drop + add and lose data; CHECK constraints are not detected, so add them by hand). Data
    migrations get their own revision and a test.
11. **SQLAlchemy notes:** use `.is_(None)`, not `is None`, in queries; a JSON column comes
    back as dicts and lists, with string keys (a dict keyed by id needs `d[str(q.id)]`) and
    lists where tuples went in, so type it with `list`; in-place edits of a JSON value are not
    saved (assign a new one); `None` in a JSON column is the JSON value `null`, `sa.null()` is
    SQL `NULL`; a `selectinload` chain is one path, so load siblings as separate options; use
    `selectinload` to avoid N+1 queries.
12. **Owned content (from 2.0).** Passages, grammar questions and speaking sets have
    `owner_id` (the author, `ON DELETE SET NULL`) and `is_common` (visibility). A CHECK keeps
    every row either common or owned (`Owned` mixin, `common_or_owned()`). Visible: common or
    mine. Editable: mine while private; common only for admins. Queries filter with
    `visible(Model, user)`; rows load through `load_visible(db, user, Model, id)` /
    `load_editable(...)` in `core/permissions.py`, which return `None` (answer 404); routes
    never call `db.get()` on owned content. Account deletion removes the user's private
    content before the user row.
13. **Imports between features.** `core/` imports no feature at runtime. Model files start
    with `from __future__ import annotations` and import other features' models only under
    `if TYPE_CHECKING:`; SQLAlchemy finds relationship targets by class name. Services, views
    and routes may import any feature's models and services; only `main.py` imports routes,
    so a route can import from anywhere without a cycle. Entry points (`main.py`, `cli.py`,
    `migrations/env.py`, `tests/conftest.py`) import `app.models`, so every model is
    registered before the first query. `__init__.py` files stay empty. Paths
    come from `BASE_DIR` / `APP_DIR` in `core/config.py`, never from `__file__` elsewhere.
14. **Translations.** Messages are English. Python calls `_()` and `ngettext()`, templates
    `_()` and `{% trans %}`; `_` is never a throwaway name. Text defined at import time is
    marked with `N_()` and translated where it is shown. Write whole sentences with named
    placeholders, never fragments glued together. JS text goes through the JSON block in
    `base.html`, with `{name}` placeholders. `/api` errors stay English. After changing any
    text, run `pybabel extract` and `update`, then translate `ru` and `uz`.
15. **Attempts read their own copy.** Starting an attempt copies what it shows into
    `attempt.content` (`copy_passage()`). The attempt page, grading, autosave and the result
    page read that copy, never the live passage; `Attempt` has no `passage` relationship.
    Answers store ids from the copy with no foreign keys, so the service checks them
    (`has_option()`). Editing or deleting content never changes a result: a deleted passage
    only sets `passage_id` to NULL.

## Tests

- Three levels: pure rules (no DB), services (real DB per test), routes (`TestClient`).
  Fixtures in `tests/conftest.py`, builders in `tests/factories.py` (question N has options
  N1, N2, N3).
- A bug fix starts with a test that fails because of the bug.
- `tests/test_migrations.py` runs Alembic on the test database: data migrations (and
  downgrades that change data), and every CHECK and partial index in the models exists after
  `upgrade head`.
- Merge only when CI is green. SQLAlchemy warnings fail the run (`filterwarnings` in
  `pyproject.toml`).
- `tests/conftest.py` pins the settings tests depend on, so a local `.env` can't change them.
  The test client sends the `ru` language cookie, so page tests check the Russian text.
- `tests/test_i18n.py` fails when a catalog misses a message from the code, or has a fuzzy,
  stale or untranslated entry, or a broken placeholder.

## Known issues in 1.0 (to fix in 2.0)

- `passages.glossary` exists but nothing uses it yet.
- The × that deletes a result on the profile has no confirm dialog (Discard has one).
