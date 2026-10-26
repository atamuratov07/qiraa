# Qiraa · قراءة

Qiraa is a small web app for practising Arabic reading comprehension. You read a passage,
answer its multiple-choice questions, and get a score with explanations; grammar questions
are practised in random sessions. It keeps a daily practice streak and a profile with your
results. It was built to prepare for an Arabic language assessment (similar to IELTS for
English) and as a project for learning FastAPI, SQLAlchemy and Alembic.

**Version 2.0.0** · live at `https://qiraa-lab2.onrender.com`

Version history: [CHANGELOG.md](CHANGELOG.md).

---

## What it does

- **Accounts.** Sign up with an invite code, log in, log out, delete your account. Sign-ups
  can also be closed completely.
- **Interface in Uzbek, Russian and English**, chosen from the header. A logged-in user's
  choice is saved with the account.
- **Personal and common content.** Every passage and grammar question is either private
  (only its author sees and edits it) or common (everyone sees it, admins edit it).
- **Passage list**, grouped by level (A2, B1). Each card shows your best score, how many
  times you submitted it, and an unfinished attempt if you have one, with Continue and
  Discard.
- **Practice.** The passage stays hidden behind a start card until you start, so the timer
  only runs while you can read it.
  - Answer options are shuffled for each attempt and keep that order when you come back.
  - Every pick is saved immediately, so closing the tab loses nothing.
  - The timer counts time actually spent on the page. After more than 30 seconds away, the
    attempt opens behind a "Paused" card with Continue and "Discard and start over".
  - Questions come one at a time, with a bar at the bottom of the screen: previous and
    next, a grid of question numbers (answered, current, flagged) and "Check answers",
    which opens a review of unanswered questions before submitting. Keys: ←/→, 1–6 to
    pick an option, F to flag. Without JavaScript the questions are a plain list.
  - The result page shows your answer, the correct one, an explanation and the Russian
    translation of the passage, with the same question grid.
- **Grammar practice.** `/grammar` starts a session of any size from common and my
  questions, or only mine. One session can be open at a time.
- **Word translation.** Tapping an Arabic word, or selecting a phrase, opens a popup with
  its translation into Uzbek, Russian or English from MyMemory, and a Google Translate link.
- **Managing content.** Editors for passages and grammar questions, and an import page for
  each kind that reads YAML files, with errors shown by line. A prompt on the import page
  tells a chatbot how to turn any material into that format. Editing or deleting content
  never changes past results: each attempt keeps a copy of what it showed.
- **Streak.** Submitting at least one passage or grammar session a day keeps the streak
  going. Days are counted in Tashkent time, so a quiz at 01:00 counts for the new day.
- **Profile.** Current and longest streak, passages started, quizzes taken, questions
  answered and accuracy; a calendar of the last 35 days; the 10 latest results, each with a ×
  button that deletes it in the background.
- **Content** is Arabic or English and takes its direction from its own text.

## Tech stack

| Part                    | Choice                                                                                 |
| ----------------------- | -------------------------------------------------------------------------------------- |
| Language                | Python 3.13                                                                            |
| Web framework           | FastAPI, with pages rendered on the server from Jinja2 templates                       |
| Database access         | SQLAlchemy 2.1 (typed `Mapped[...]` models), Alembic migrations                        |
| Validation and settings | Pydantic v2, pydantic-settings                                                         |
| Passwords               | Argon2id (argon2-cffi)                                                                 |
| Translations            | Babel, gettext catalogs read at startup, Jinja's i18n extension                        |
| Time zones              | `zoneinfo` with the `tzdata` package                                                   |
| Database                | Postgres 18: Neon in production, Docker Compose locally and for tests                  |
| Frontend                | Tailwind CSS v4 browser build and Alpine.js from CDNs, plain JavaScript, no build step |
| Word translation        | MyMemory, called from the browser                                                      |
| Packages                | uv (`pyproject.toml` + `uv.lock`)                                                      |
| Tests                   | pytest with FastAPI's `TestClient`                                                     |
| Hosting                 | Docker image on Render                                                                 |

## Hosting

| Part     | Service                             | Notes                                                                                                                |
| -------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| App      | Render, free web service, Frankfurt | Built from the `Dockerfile` on every push to `main`. The container runs `alembic upgrade head`, then starts Uvicorn. |
| Database | Neon, free Postgres, Frankfurt      | Render's own free Postgres is deleted after 30 days, which is why Neon is used.                                      |

On Render, set `DATABASE_URL` (Neon's pooled connection string), `SECURE_COOKIES=true`,
`SIGNUP_CODE`, and optionally `MIGRATION_DATABASE_URL` (Neon's direct connection string,
used only by Alembic).

The free Render instance sleeps after 15 minutes without visitors. The first request after
that takes about a minute.

## Running it locally

Requires [uv](https://docs.astral.sh/uv/) and Docker. Postgres runs in Docker; the app runs
on your machine.

```bash
docker compose up -d --wait db   # Postgres 18 on port 5432, returns once it accepts connections
uv sync                          # creates .venv and installs everything from uv.lock
uv run alembic upgrade head      # creates the tables in the qiraa database
uv run fastapi dev app/main.py   # http://127.0.0.1:8000, restarts on every save
```

Open the address and sign up. Then load the example passage into your account, and make
yourself an admin to edit common content:

```bash
uv run python -m app.cli import content/example.yaml --owner <username>
uv run python -m app.cli make-admin <username>
```

The interactive API page is at `/docs`.

The Compose database keeps its data in a Docker volume between restarts. On the first start
it creates two databases, `qiraa` for the app and `qiraa_test` for the tests
(`docker/initdb/01-test-db.sql`). `docker compose down -v` deletes the volume, and the next
`up` starts from empty databases.

### Settings

Read from environment variables, or from a `.env` file in the project root (copy
`.env.example`). Environment variables win over `.env`.

| Variable                 | Default                                         | Meaning                                                                      |
| ------------------------ | ----------------------------------------------- | ---------------------------------------------------------------------------- |
| `DATABASE_URL`           | `postgresql://qiraa:qiraa@localhost:5432/qiraa` | the app's database; the default is the Compose one; Neon's URL in production |
| `MIGRATION_DATABASE_URL` | same as `DATABASE_URL`                          | the database Alembic migrates, if it should differ                           |
| `SECURE_COOKIES`         | `false`                                         | `true` in production, so the session cookie is only sent over HTTPS          |
| `SESSION_DAYS`           | `30`                                            | how long a login lasts                                                       |
| `APP_TIMEZONE`           | `Asia/Tashkent`                                 | the time zone that decides what "today" means for streaks and dates          |
| `ALLOW_SIGNUP`           | `true`                                          | `false` closes sign-up completely                                            |
| `SIGNUP_CODE`            | none                                            | when set, sign-up asks for this code; share it with the people you invite    |

`postgres://` and `postgresql://` URLs are converted to the `postgresql+psycopg://` form
SQLAlchemy needs, so Neon's connection strings can be pasted as they are.

## Tests

```bash
docker compose up -d --wait db   # if it isn't running yet
uv run pytest                    # all tests, on the qiraa_test database
uv run pytest -k streak          # only tests with "streak" in the name
```

Every test drops and recreates all tables in `qiraa_test`. `TEST_DATABASE_URL` points the
tests at another database (in the `postgresql+psycopg://...` form); use one made only for
tests. When the database can't be reached, the run stops with
`Test database not reachable. Start it: docker compose up -d --wait db`.

The suite has 226 tests:

| File                       | Tests | Covers                                                                   |
| -------------------------- | ----- | ------------------------------------------------------------------------ |
| `test_config.py`           | 3     | reading settings from `.env` (no database)                               |
| `test_attempt_rules.py`    | 19    | timer rule, grading (plain objects, no database)                         |
| `test_passage_rules.py`    | 2     | a passage's title, or the start of its text                              |
| `test_attempt_service.py`  | 21    | attempt service functions, including simulated double-click races        |
| `test_attempt_routes.py`   | 14    | the practice journey over HTTP, attempt copies, access checks, bad input |
| `test_grammar_sessions.py` | 7     | grammar sessions: pools, sizes, one open session                         |
| `test_navigator.py`        | 2     | the question grid on the attempt and result pages                        |
| `test_permissions.py`      | 23    | owner, other user and admin against view, edit, delete and practise      |
| `test_account_deletion.py` | 2     | private content goes with the account, common content stays              |
| `test_signup.py`           | 6     | sign-up, the invite code                                                 |
| `test_language.py`         | 11    | choosing the interface language                                          |
| `test_i18n.py`             | 11    | catalogs have every message, no stale or broken entries                  |
| `test_content_schema.py`   | 9     | the content file rules                                                   |
| `test_content_loader.py`   | 10    | YAML parsing and error line numbers                                      |
| `test_content_import.py`   | 5     | importing and updating by slug                                           |
| `test_content_files.py`    | 3     | every `content/*.yaml` file parses                                       |
| `test_import_routes.py`    | 12    | the import pages                                                         |
| `test_cli.py`              | 6     | `make-admin`, `import` and `check`                                       |
| `test_passage_editing.py`  | 6     | creating and updating passages                                           |
| `test_manage_routes.py`    | 12    | the passage manage pages and editor                                      |
| `test_grammar_manage.py`   | 7     | the grammar manage pages and editor                                      |
| `test_streaks.py`          | 19    | Tashkent dates, streak rules, streaks through submitting                 |
| `test_profile.py`          | 10    | profile numbers and calendar, profile pages, deleting results            |
| `test_migrations.py`       | 6     | data migrations, and every CHECK and partial index after `upgrade head`  |

A SQLAlchemy warning (for example a query that forgot a join) fails the test run.

### CI

`.github/workflows/tests.yml` runs on every push, against a Postgres 18 service container.
It installs the locked dependencies, then:

1. applies all migrations to an empty database (`alembic upgrade head`);
2. fails if a model changed without a migration (`alembic check`);
3. runs every migration's `downgrade()` back to empty (`alembic downgrade base`);
4. runs the test suite.

The result shows in the repository's Actions tab.

## Changing the app

**Deploying:** push to `main`. Render builds the image, applies new migrations and restarts.

**Changing a model:**

```bash
uv run alembic revision --autogenerate -m "add something"   # writes a migration
# read the generated file in migrations/versions/ before applying it
uv run alembic upgrade head                                 # apply locally first
```

Commit the migration together with the model change. Production applies it on the next
deploy. Never edit a migration that has already run on Neon; write a new one instead. A new
column on a table that already has rows needs a `server_default` (or must be nullable),
otherwise the migration fails on existing rows.

**Changing interface text:** messages are English in the code and templates. After changing
any, update the catalogs and translate the new entries in `app/locale/ru` and `app/locale/uz`:

```bash
uv run pybabel extract -F babel.cfg --project=Qiraa --version=2.0.0 --width=88 -o app/locale/messages.pot .
uv run pybabel update -i app/locale/messages.pot -d app/locale --width=88 --ignore-obsolete
```

**Adding content:** in the app, through the editors or the import pages under "Manage"
(`/manage/passages`, `/manage/grammar`). From the command line, a YAML file holds one kind
of content, under a `passages:` or a `grammar:` key; `content/example.yaml` shows a passage,
and each import page's prompt shows its kind. Every other `.yaml` file in `content/` is
ignored by git, so real content stays on your machine. Check a file, then import it into
one user's private area, locally and against Neon:

```bash
uv run python -m app.cli check content/my-passages.yaml
uv run python -m app.cli import content/my-passages.yaml --owner <username>
DATABASE_URL="postgresql://..." uv run python -m app.cli import content/my-passages.yaml --owner <username>
```

`--common` instead of `--owner` imports content that every user sees. Every entry has a
slug written by hand; an entry whose slug is already loaded is updated, so the import can
run any number of times. Results of earlier attempts keep the version they were taken on.

## How it works

### Accounts and sessions

- Passwords are stored as Argon2id hashes (64 MiB of memory and 3 passes per check). The salt
  is part of the stored hash string. Hashes made with older settings are upgraded at the next
  login.
- Logging in creates a 256-bit random token with Python's `secrets` module. The browser keeps
  it in the `qiraa_session` cookie, marked `HttpOnly`, `SameSite=Lax`, and `Secure` in
  production. The database stores only the token's SHA-256 hash, so a leaked `sessions` table
  can't be used to log in.
- Logging out deletes the session row, so the cookie stops working at once. Expired sessions
  are deleted the next time they are used.
- A wrong password and an unknown username get the same message and take about the same
  time, so the login form doesn't reveal which usernames exist. A wrong invite code is
  compared in constant time and gets a form error like a taken username.
- After logging in, `next` is followed only if it is a path on this site (`/profile`, not
  `//other.site`). A form sent while logged out brings you back to the page it was on.
- Pages redirect to `/login` when you aren't logged in. JSON endpoints under `/api` answer `401`.
- Admins are set from the command line only (`make-admin`).

### Content and permissions

Passages and grammar questions have an author (`owner_id`) and a visibility (`is_common`).
I see common content and my own; I edit my own private content, and admins edit common
content. Only admins publish (make content common). Someone else's private content answers
`404` everywhere, as if it didn't exist.

Deleting an account deletes its private content first, then the user. Common content stays
with no author, so other users keep their results on it. A CHECK keeps every row either
common or owned, so a deletion that forgot the private content fails instead of leaving rows
nobody can reach.

### Attempts

```
POST /passages/{pid}/attempts
POST /grammar/sessions           ──▶ OPEN ──── POST /attempts/{aid}/submit ──▶ SUBMITTED (read-only)
                                       │
                                       └── POST /attempts/{aid}/discard ──▶ deleted
```

- **Two kinds.** A passage attempt and a grammar session share the `attempts` table, the
  attempt page and the result layout; `kind` tells them apart.
- **A copy of the content.** Starting an attempt copies what it shows into
  `attempts.content`: the title, the text, the translation, and the questions with their
  options in shuffled order, the correct one marked. The attempt page, autosave, grading and
  the result page read that copy, so editing or deleting the passage later never changes a
  result. A grammar session copies a random choice of questions from its pool.
- **One open attempt per passage, and one open grammar session per user**, enforced by
  partial unique indexes. A double click on Start returns the attempt created first.
- **Autosave.** Each pick sends `PUT /api/attempts/{attempt_id}/answers/{question_id}`. The
  server checks that the option belongs to that question in the attempt's copy, then
  updates the saved answer or inserts it.
- **Timer.** While the page is open, the browser sends a heartbeat every 15 seconds. The server
  adds the time since the previous heartbeat only if that gap is 30 seconds or less. Example:
  heartbeats at 10:00:00, 10:00:15 and 14:30:00 add 15 seconds and then nothing. The server
  owns `elapsed_seconds`; the page only displays it.
- **Submitting** saves the answers in the form as well (in case an autosave failed), counts the
  last heartbeat, grades, updates the streak and sets `submitted_at`, all in one database
  commit.
- **Flags** for the review stay in the browser (`localStorage`, per attempt) and are removed
  when the attempt is submitted or discarded.
- **Access.** Another user's attempt answers `404`, so its existence isn't revealed. Changing
  a submitted attempt answers `409`; the page then reloads and shows the result.

### Streaks

Each user row stores `current_streak`, `longest_streak` and `last_active_on`. Submitting a quiz
on the day after `last_active_on` adds one; a second quiz on the same day changes nothing;
a gap of a day or more starts again at 1. Nothing runs at midnight, so pages show the stored
streak only if the last practice day was today or yesterday, and 0 otherwise. Deleting a result
doesn't change the streak.

### Languages

The interface language comes from the `qiraa_lang` cookie (set from the account at login),
then the browser's `Accept-Language`, then English. Messages are English in the code, so
English needs no catalog; `ru` and `uz` catalogs are read from the `.po` files at startup.
Dates and plural forms follow each language's rules through Babel. Errors under `/api` stay
English.

### Word translation

`reader.js` wraps every Arabic word on the attempt and result pages in a tappable span. A tap,
or a selection of up to 500 characters, asks MyMemory directly from the browser (it allows
this with `Access-Control-Allow-Origin: *`), so each user has MyMemory's anonymous quota of
5,000 characters a day for their own address. The popup's language buttons pick Uzbek,
Russian or English (the interface language by default, remembered in the browser), and
answers are kept for the browser session.

### Conventions in the code

The full list is in [docs/CONVENTIONS.md](docs/CONVENTIONS.md). The main ones:

- Code is organised by feature. Each content feature (`passages/`, `grammar/`) owns its
  models, file format, import, editor and how an attempt on it starts; `practice/` holds
  what every attempt shares once it has started.
- Routes stay thin: they read the request, call a function in the feature's `service.py`, and
  choose the response. Services contain no HTTP code, which makes them easy to test.
- Service functions take the current time as a `now` parameter instead of reading the clock,
  so tests can use fixed times.
- Pages are rendered through `render()` with a typed context (a `TypedDict` from the feature's
  `views.py`). Jinja runs with `StrictUndefined`, so a misspelled variable raises an error
  instead of rendering as an empty string.
- Times are stored in UTC (`timestamptz` columns). `as_utc()` treats a time without a time zone
  as UTC before any comparison, and `local_day()` turns a stored time into a Tashkent date.

## Routes

| Method    | Path                                               | What it does                                                        | Response                                                             |
| --------- | -------------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------- |
| GET       | `/`                                                | Sends you to the passage list                                       | 303 to `/passages`                                                   |
| GET, POST | `/signup`                                          | Show the form; create the account and log in                        | `auth/signup.html`; 303 to `/passages`; 403 when sign-ups are closed |
| GET, POST | `/login`                                           | Show the form; check the password                                   | `auth/login.html`; 303 to `next`                                     |
| POST      | `/logout`                                          | Delete the session                                                  | 303 to `/login`                                                      |
| POST      | `/settings/language`                               | Field `locale` (`uz`, `ru`, `en`): set the interface language       | 303 to the form's `next`                                             |
| GET       | `/profile`                                         | Streaks, statistics, calendar, latest results, account deletion     | `profile/profile.html`                                               |
| POST      | `/account/delete`                                  | Delete the account after checking the password                      | 303 to `/login`; 400 with the profile page on a wrong password       |
| GET       | `/passages`                                        | Passage list with best score, tries and unfinished attempts         | `passages/list.html`                                                 |
| GET       | `/passages/{pid}`                                  | Start card for a passage                                            | `passages/start.html`; 303 to the open attempt if there is one       |
| POST      | `/passages/{pid}/attempts`                         | Start an attempt (or return the open one)                           | 303 to `/attempts/{aid}`                                             |
| GET       | `/grammar`                                         | Start form for a grammar session, or the open session's card        | `grammar/start.html`                                                 |
| POST      | `/grammar/sessions`                                | Fields `pool` and `size`: start a session                           | 303 to `/attempts/{aid}`; 400 when the pool is empty                 |
| GET       | `/attempts/{aid}`                                  | Your own attempt: the attempt page while open, the result once done | the kind's `attempt.html` or `result.html`                           |
| POST      | `/attempts/{aid}/submit`                           | Form fields `q<question id>=<option id>`; grade and close           | 303 to `/attempts/{aid}`                                             |
| POST      | `/attempts/{aid}/discard`                          | Delete an open attempt and its answers                              | 303 to the form's `next`; 409 if already submitted                   |
| POST      | `/attempts/{aid}/delete`                           | Delete a result (any attempt of yours)                              | 303 to the form's `next`, default `/profile`                         |
| GET       | `/manage/passages`, `/manage/grammar`              | My content, and common content for admins                           | the kind's `manage.html`                                             |
| GET, POST | `/manage/{passages,grammar}/new`                   | The editor; create from its JSON field                              | the kind's `editor.html`; 303 to the manage page                     |
| GET, POST | `/manage/{passages,grammar}/{id}/edit`             | The editor; save                                                    | the kind's `editor.html`; 303 to the manage page; 404 if not mine    |
| POST      | `/manage/{passages,grammar}/{id}/delete`           | Delete one item                                                     | 303 to the manage page; 404 if not mine                              |
| GET, POST | `/manage/{passages,grammar}/import`                | Paste or upload a YAML file; import it                              | `content/import.html` with the report, or 400 with errors by line    |
| PUT       | `/api/attempts/{attempt_id}/answers/{question_id}` | JSON `{"option_id": 45}`: save or replace one answer                | 204; 400 for an option not in the attempt; 409 if submitted          |
| POST      | `/api/attempts/{attempt_id}/heartbeat`             | Apply the timer rule                                                | `{"elapsed_seconds": 192}`; 409 if submitted                         |
| GET       | `/healthz`                                         | Health check used by Render                                         | `{"ok": true}`                                                       |

Errors on pages are shown in the interface language on `error.html`; errors under `/api` are
JSON `{"detail": "..."}` in English. A malformed page URL (for example `/passages/abc`) shows
the 404 page.

## Data model

```
users ──< sessions
users ──< attempts ──< attempt_answers
users ──< passages ──< passage_questions ──< passage_options        (owner_id, nullable)
users ──< grammar_questions ──< grammar_options                     (owner_id, nullable)
          attempts >── passages                                     (passage_id, nullable)
```

`─<` means one-to-many: one user has many sessions.

```
users
  id                int, primary key
  username          str(32), unique         CHECK: stored in lower case
  password_hash     str                     Argon2id hash, never the password
  is_admin          bool, default false     set with the make-admin command
  locale            str(8), nullable        "uz" | "ru" | "en"; NULL until chosen
  created_at        datetime
  current_streak    int, default 0
  longest_streak    int, default 0
  last_active_on    date, nullable          the last day a quiz was submitted (Tashkent time)

sessions
  id                int, primary key
  token_hash        str(64), unique         SHA-256 of the cookie token
  user_id           → users.id              deleted with the user
  expires_at        datetime

passages
  id                int, primary key        used in URLs
  owner_id          → users.id, nullable    the author; NULL once a common passage's author
                                            deletes their account
  is_common         bool, default false     everyone sees it
  slug              str(80), nullable       e.g. "b1-media", from content files; lets an
                                            import update a passage
  title             str(200), nullable      when missing, the start of the text is shown
  level             str, default ""         e.g. "A2"; never NULL, the list groups by it
  text              text                    a blank line starts a new paragraph
  translation_ru    text, nullable

  CHECK: is_common OR owner_id IS NOT NULL
  unique (slug) WHERE is_common, and (owner_id, slug) WHERE NOT is_common

passage_questions
  id                int, primary key
  passage_id        → passages.id           deleted with the passage
  position          int                     display order; unique per passage
  prompt            text
  explanation       text, nullable          shown on the result page

passage_options
  id                int, primary key
  question_id       → passage_questions.id  deleted with the question
  position          int                     unique per question
  text              text
  is_correct        bool

  unique (question_id) WHERE is_correct
    → at most one correct option per question

grammar_questions
  id, owner_id, is_common, slug             as in passages, with the same CHECK and indexes
  prompt            text
  explanation       text, nullable

grammar_options                             as passage_options, for grammar_questions

attempts
  id                int, primary key
  user_id           → users.id              deleted with the user
  kind              str                     "passage" | "grammar"
  passage_id        → passages.id, nullable NULL for a grammar session, and once the
                                            passage is deleted (the attempt stays)
  content           JSON                    the copy the attempt shows: title, level, text,
                                            translation_ru, questions with their options
                                            in display order, the correct one marked
  started_at        datetime
  last_seen_at      datetime                last heartbeat, for the timer rule and "paused"
  elapsed_seconds   int, default 0          time actually spent on the page
  submitted_at      datetime, nullable      NULL while the attempt is open
  score             int, nullable           set on submit
  total             int, nullable           set on submit

  CHECK: kind IN ('passage', 'grammar'), and kind = 'passage' OR passage_id IS NULL
  unique (user_id, passage_id) WHERE submitted_at IS NULL
    → at most one open attempt per passage
  unique (user_id) WHERE submitted_at IS NULL AND kind = 'grammar'
    → at most one open grammar session per user

attempt_answers
  id                int, primary key
  attempt_id        → attempts.id           deleted with the attempt
  question_id       int                     an id inside attempts.content, no foreign key
  option_id         int                     an id inside attempts.content, no foreign key

  unique (attempt_id, question_id)
    → choosing a different option updates the row instead of adding a second one
```

Constraint and index names follow a naming convention set on `Base.metadata`, so Alembic
generates predictable names that later migrations can refer to. The 1.0 schema is the
single migration `migrations/versions/6ad753184ecc_initial_schema.py`; each 2.0 change has
its own revision after it, data migrations included.

## Project structure

```
qiraa/
├── .github/workflows/
│   └── tests.yml          CI: migrations and tests on Postgres for every push
├── app/
│   ├── main.py            creates the app: static files, routes, error pages, /healthz
│   ├── models.py          imports every model, for Alembic and the tests
│   ├── cli.py             make-admin, import, check
│   ├── core/              shared by every feature: Base and the Owned mixin, settings,
│   │                      database session, permissions (visible(), editable()),
│   │                      translations (i18n.py), templating, time helpers, redirects
│   ├── auth/              User, UserSession; sign-up with the invite code, login, logout,
│   │                      language setting, account deletion; password hashing and tokens
│   ├── passages/          Passage, PassageQuestion, PassageOption; passage list and start
│   │                      card; starting an attempt; file schema, prompt, import, editor
│   ├── grammar/           GrammarQuestion, GrammarOption; sessions and the start page;
│   │                      file schema, prompt, import, editor
│   ├── content/           what content files share: question schema, YAML loader with
│   │                      line numbers, errors, the import pages
│   ├── practice/          Attempt, AttemptAnswer; autosave, timer rule, grading; the
│   │                      shared attempt and result layouts, the question grid; JSON API
│   ├── profile/           streak rules; profile statistics, calendar, latest results
│   ├── locale/            messages.pot and the ru and uz catalogs
│   ├── templates/         base, error, shared macros, plus one folder per feature
│   └── static/
│       ├── reader.js      tappable Arabic words and the translation popup
│       ├── attempt.js     timer, pause and resume, autosave
│       ├── navigator.js   one question at a time, the grid, flags, the review (Alpine)
│       ├── editor.js      the passage and grammar editors (Alpine)
│       └── forms.js       background forms, data-forget, menus
├── content/               example.yaml; other content files stay local (ignored by git)
├── docker/initdb/         SQL run on the first start of the Compose database
├── docs/                  CONVENTIONS.md, ROADMAP.md, CONTENT-LOADER.md
├── migrations/            Alembic environment and revisions
├── tests/                 conftest.py, factories.py and one file per area
├── .env.example           settings for local development, to copy to .env
├── alembic.ini
├── babel.cfg              where pybabel looks for messages
├── docker-compose.yml     Postgres for development and tests
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

Each feature folder holds the same kinds of files where it needs them: `models.py` (tables),
`service.py` (database work and rules, no HTTP), `routes.py` (pages and form posts) and
`views.py` (what each template receives); `practice/` also has `api.py` with `schemas.py` for
the JSON endpoints. Templates are in `app/templates/<feature>/`.

## Known limitations

- Tailwind is compiled in the browser from a CDN and logs a "not for production" warning in
  the console.
- There is no password reset and no limit on login attempts; sign-up needs the invite code.
- MyMemory translates a word without its sentence, so a word with several meanings can get
  the wrong one.

## Roadmap

Ideas for after 2.0, such as speaking practice, accounts with an email and password reset,
personal invite codes and word meanings in context, are in [docs/ROADMAP.md](docs/ROADMAP.md).
