# Qiraa · قراءة

Qiraa is a small web app for practising Arabic reading comprehension. You open a passage,
read it, answer its multiple-choice questions, and get a score with explanations in Russian.
It also keeps a daily practice streak and a profile with your results. It was built to prepare
for an Arabic language assessment (similar to IELTS for English) and as a project for learning
FastAPI, SQLAlchemy and Alembic.

**Version 1.0.0** · 10 October 2026 · live at `https://<your-app>.onrender.com`

The interface is in Russian. Version history: [CHANGELOG.md](CHANGELOG.md).

---

## What it does

- **Accounts.** Sign up, log in, log out, delete your account. Sign-ups can be closed with a
  setting once your own accounts exist.
- **Passage list**, grouped by level (A2, B1), with your daily streak at the top. Each card
  shows your best score, how many times you submitted it, and an unfinished attempt if you have
  one, with Resume and Discard buttons. Discarding happens in the background, without a reload.
- **Practice.** The passage stays hidden behind a "Start practice" card until you start, so
  the timer only runs while you can read it.
  - Answer options are shuffled for each attempt and keep that order when you come back.
  - Every pick is saved immediately, so closing the tab loses nothing.
  - The timer counts time actually spent on the page. After more than 30 seconds away, the
    attempt opens behind a "Paused" card with Resume and "Discard and start over".
  - Submitting shows the review: your answer, the correct one, an explanation and the Russian
    translation of the passage.
- **Streak.** Submitting at least one quiz a day keeps the streak going. Days are counted in
  Tashkent time, so a quiz at 01:00 counts for the new day.
- **Profile.** Current and longest streak, quizzes taken, questions answered, accuracy and
  passages tried; a calendar of the last 35 days; the 10 latest results, each with a × button
  that deletes it in the background.
- **Content.** Four real passages (two A2, two B1; 24 questions), loaded by `app/seed.py`.
- **Arabic text** is shown right to left in Noto Naskh Arabic. Tapping a word opens a small
  popup with a Google Translate link. The built-in dictionary comes in a later version.

### Not in 1.0 yet

| Feature | Status |
|---|---|
| Word translation inside the popup | planned; the `passages.glossary` column already exists |
| Adding or editing passages without changing code | planned for 2.0 |
| Interface in Uzbek and English | planned for 2.0 |

See [Roadmap](#roadmap).

## Tech stack

| Part | Choice |
|---|---|
| Language | Python 3.13 |
| Web framework | FastAPI, with pages rendered on the server from Jinja2 templates |
| Database access | SQLAlchemy 2.1 (typed `Mapped[...]` models), Alembic migrations |
| Validation and settings | Pydantic v2, pydantic-settings |
| Passwords | Argon2id (argon2-cffi) |
| Time zones | `zoneinfo` with the `tzdata` package |
| Database | Postgres on Neon in production, SQLite locally |
| Frontend | Tailwind CSS v4 browser build from a CDN, three plain JavaScript files, no build step |
| Packages | uv (`pyproject.toml` + `uv.lock`) |
| Tests | pytest with FastAPI's `TestClient` |
| Hosting | Docker image on Render |

Exact versions are pinned in `uv.lock`.

## Hosting

| Part | Service | Notes |
|---|---|---|
| App | Render, free web service, Frankfurt | Built from the `Dockerfile` on every push to `main`. The container runs `alembic upgrade head`, then starts Uvicorn. |
| Database | Neon, free Postgres, Frankfurt | Render's own free Postgres is deleted after 30 days, which is why Neon is used. |
| Domain | `*.onrender.com` | A free `yourname.is-a.dev` subdomain can be requested through a pull request to github.com/is-a-dev/register and pointed at Render. |

On Render, set `DATABASE_URL` (Neon's pooled connection string), `SECURE_COOKIES=true`, and
optionally `MIGRATION_DATABASE_URL` (Neon's direct connection string, used only by Alembic).

The free Render instance sleeps after 15 minutes without visitors. The first request after
that takes about a minute.

## Running it locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # creates .venv and installs everything from uv.lock
uv run alembic upgrade head      # creates the tables in dev.db (SQLite) in the project root
uv run python -m app.seed        # loads the four passages
uv run fastapi dev app/main.py   # http://127.0.0.1:8000, restarts on every save
```

Open the address, sign up, and pick a passage. The interactive API page is at `/docs`.

### Settings

Read from environment variables.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///<project>/dev.db` | the app's database; Neon's `postgresql://...` URL in production |
| `MIGRATION_DATABASE_URL` | same as `DATABASE_URL` | the database Alembic migrates, if it should differ |
| `SECURE_COOKIES` | `false` | `true` in production, so the session cookie is only sent over HTTPS |
| `SESSION_DAYS` | `30` | how long a login lasts |
| `APP_TIMEZONE` | `Asia/Tashkent` | the time zone that decides what "today" means for streaks and dates |
| `ALLOW_SIGNUP` | `true` | set to `false` once your own accounts exist |

`postgres://` and `postgresql://` URLs are converted to the `postgresql+psycopg://` form
SQLAlchemy needs, so Neon's connection strings can be pasted as they are.

## Tests

```bash
uv run pytest                    # a fresh SQLite database for every test
uv run pytest -k streak          # only tests with "streak" in the name
TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/qiraa_test uv run pytest
```

`TEST_DATABASE_URL` runs the same tests against Postgres. Use a database made only for tests:
every test drops and recreates all tables.

The suite has 88 tests:

| File | Tests | Covers |
|---|---|---|
| `test_attempt_rules.py` | 19 | timer rule, grading, option order (plain objects, no database) |
| `test_attempt_service.py` | 19 | attempt service functions, including two simulated double-click races |
| `test_attempt_routes.py` | 9 | the full practice journey over HTTP, access checks, bad input |
| `test_streaks.py` | 19 | Tashkent dates, streak rules, streaks through submitting |
| `test_profile.py` | 22 | profile numbers and calendar, profile pages, deleting results |

A SQLAlchemy warning (for example a query that forgot a join) fails the test run.

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

**Adding passages:** passages are entries of the `PASSAGES` list in `app/seed.py`. Each entry
has a `slug`, `title`, `level`, `text`, `translation_ru` and its questions; each question has
a `prompt`, its `options`, the correct `answer` as a letter, and an `explanation`. Then run the
seed locally and against Neon:

```bash
uv run python -m app.seed
DATABASE_URL="postgresql://..." uv run python -m app.seed               # macOS / Linux
$env:DATABASE_URL="postgresql://..."; uv run python -m app.seed         # Windows PowerShell
```

Passages whose slug already exists are skipped, so the script can run any number of times.
To change a passage that is already loaded, delete it from the database and run the seed
again. Deleting a passage also deletes its attempts.

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
  time, so the login form doesn't reveal which usernames exist.
- After logging in, `next` is followed only if it is a path on this site (`/profile`, not
  `//other.site`).
- Pages redirect to `/login` when you aren't logged in. JSON endpoints under `/api` answer `401`.
- Deleting an account deletes its sessions and attempts (`ON DELETE CASCADE`).

### Attempts

```
POST /passages/{pid}/attempts        POST /attempts/{aid}/submit
──────────────────────────────▶ OPEN ──────────────────────────▶ SUBMITTED (read-only)
                                  │
                                  └── POST /attempts/{aid}/discard ──▶ deleted
```

- **One open attempt per passage.** A partial unique index on `attempts (user_id, passage_id)
  WHERE submitted_at IS NULL` enforces it in the database. A double click on Start returns the
  attempt that was created first.
- **Shuffled options.** The order is chosen when the attempt starts and saved in
  `attempts.option_order`, so a reload or the result page shows the same order.
- **Autosave.** Each pick sends `PUT /api/attempts/{attempt_id}/answers/{question_id}`. The
  server checks that the option belongs to that question of this passage, then updates the
  saved answer or inserts it.
- **Timer.** While the page is open, the browser sends a heartbeat every 15 seconds. The server
  adds the time since the previous heartbeat only if that gap is 30 seconds or less. Example:
  heartbeats at 10:00:00, 10:00:15 and 14:30:00 add 15 seconds and then nothing. The server
  owns `elapsed_seconds`; the page only displays it.
- **Submitting** saves the answers in the form as well (in case an autosave failed), counts the
  last heartbeat, grades, updates the streak and sets `submitted_at`, all in one database
  commit. An option id that doesn't belong to its question is ignored, and that question keeps
  its autosaved answer.
- **Access.** Another user's attempt answers `404`, so its existence isn't revealed. Changing
  a submitted attempt answers `409`; the page then reloads and shows the result.

### Streaks

Each user row stores `current_streak`, `longest_streak` and `last_active_on`. Submitting a quiz
on the day after `last_active_on` adds one; a second quiz on the same day changes nothing;
a gap of a day or more starts again at 1. Nothing runs at midnight, so pages show the stored
streak only if the last practice day was today or yesterday, and 0 otherwise. Deleting a result
doesn't change the streak.

### Conventions in the code

- Routes stay thin: they read the request, call a function in `services/`, and choose the
  response. Services contain no HTTP code, which makes them easy to test.
- Service functions take the current time as a `now` parameter instead of reading the clock,
  so tests can use fixed times.
- Pages are rendered through `render()` with a typed context (a `TypedDict` from `views.py`).
  Jinja runs with `StrictUndefined`, so a misspelled variable raises an error instead of
  rendering as an empty string.
- Times are stored in UTC. SQLite returns them without a time zone, so `as_utc()` adds it back
  before any comparison, and `local_day()` turns a stored time into a Tashkent date.
- Templates format dates with the `local_date` filter (Russian month names) and choose Russian
  plural forms with the `plural` filter.

## Routes

| Method | Path | What it does | Response |
|---|---|---|---|
| GET | `/` | Sends you to the passage list | 303 to `/passages` |
| GET, POST | `/signup` | Show the form; create the account and log in | `signup.html`; 303 to `/passages`; 403 when sign-ups are closed |
| GET, POST | `/login` | Show the form; check the password | `login.html`; 303 to `next` |
| POST | `/logout` | Delete the session | 303 to `/login` |
| GET | `/profile` | Streaks, statistics, calendar, latest results, account deletion | `profile.html` |
| POST | `/account/delete` | Delete the account after checking the password | 303 to `/login`; 400 with the profile page on a wrong password |
| GET | `/passages` | Streak and passage list with best score, tries and unfinished attempts | `passages.html` |
| GET | `/passages/{pid}` | Start card for a passage | `passage_start.html`; 303 to the open attempt if there is one |
| POST | `/passages/{pid}/attempts` | Start an attempt (or return the open one) | 303 to `/attempts/{aid}` |
| GET | `/attempts/{aid}` | Your own attempt: practice page while open, result once submitted | `attempt.html` or `result.html` |
| POST | `/attempts/{aid}/submit` | Form fields `q<question id>=<option id>`; grade and close | 303 to `/attempts/{aid}` |
| POST | `/attempts/{aid}/discard` | Delete an open attempt and its answers | 303 to the form's `next`; 409 if already submitted |
| POST | `/attempts/{aid}/delete` | Delete a result (any attempt of yours) | 303 to the form's `next`, default `/profile` |
| PUT | `/api/attempts/{attempt_id}/answers/{question_id}` | JSON `{"option_id": 45}`: save or replace one answer | 204; 400 for an option of another question; 409 if submitted |
| POST | `/api/attempts/{attempt_id}/heartbeat` | Apply the timer rule | `{"elapsed_seconds": 192}`; 409 if submitted |
| GET | `/healthz` | Health check used by Render | `{"ok": true}` |

Errors on pages are shown in Russian on `error.html`; errors under `/api` are JSON
`{"detail": "..."}`. A malformed page URL (for example `/passages/abc`) shows the 404 page.

## Data model

```
users ──< sessions
users ──< attempts >── passages ──< questions ──< options
          attempts ──< attempt_answers   (one per question: the chosen option)
```

`─<` means one-to-many: one user has many sessions.

```
users
  id                int, primary key
  username          str(32), unique         CHECK: stored in lower case
  password_hash     str                     Argon2id hash, never the password
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
  slug              str(80), unique         e.g. "b1-media"; lets the seed skip loaded passages
  title             str
  level             str, default ""         e.g. "A2"; never NULL, the list groups by it
  text              text                    a blank line starts a new paragraph
  translation_ru    text, nullable
  glossary          JSON, default {}        {"السوق": "рынок"}; not used yet

questions
  id                int, primary key
  passage_id        → passages.id           deleted with the passage
  position          int                     display order; unique per passage
  prompt            text
  explanation       text, nullable          shown on the result page

options
  id                int, primary key
  question_id       → questions.id          deleted with the question
  position          int                     unique per question
  text              text
  is_correct        bool

  unique (question_id) WHERE is_correct
    → at most one correct option per question

attempts
  id                int, primary key
  user_id           → users.id              deleted with the user
  passage_id        → passages.id           deleted with the passage
  option_order      JSON                    {"12": [45, 43, 46, 44]}: question id → option ids
  started_at        datetime
  last_seen_at      datetime                last heartbeat, for the timer rule and "paused"
  elapsed_seconds   int, default 0          time actually spent on the page
  submitted_at      datetime, nullable      NULL while the attempt is open
  score             int, nullable           set on submit
  total             int, nullable           set on submit

  unique (user_id, passage_id) WHERE submitted_at IS NULL
    → at most one open attempt per passage

attempt_answers
  id                int, primary key
  attempt_id        → attempts.id           deleted with the attempt
  question_id       → questions.id          deleted with the question
  option_id         → options.id            deleted with the option

  unique (attempt_id, question_id)
    → choosing a different option updates the row instead of adding a second one
```

Constraint and index names follow a naming convention set on `Base.metadata`, so Alembic
generates the same names on SQLite and Postgres. The schema is created by a single migration,
`migrations/versions/6ad753184ecc_initial_schema.py`.

## Project structure

```
qiraa/
├── app/
│   ├── main.py            creates the app: static files, routers, error pages, /healthz
│   ├── config.py          settings from environment variables
│   ├── db.py              database engine, sessions, the get_db dependency
│   ├── models.py          SQLAlchemy models
│   ├── schemas.py         Pydantic shapes of the JSON the API receives and sends
│   ├── views.py           dataclasses and TypedDicts: what each template receives
│   ├── templating.py      Jinja setup, render(), Russian date and plural filters
│   ├── deps.py            current-user dependencies, reading form fields
│   ├── security.py        password hashing, session tokens
│   ├── redirects.py       safe_next(): redirects only within the site
│   ├── timeutils.py       as_utc(), local_day()
│   ├── seed.py            the passages and the script that loads them
│   ├── routers/
│   │   ├── auth.py        sign-up, login, logout, account deletion
│   │   ├── passages.py    passage list, start card, starting an attempt
│   │   ├── attempts.py    practice and result page, submit, discard, delete
│   │   ├── api.py         JSON for attempt.js: autosave, heartbeat
│   │   └── profile.py     the profile page
│   ├── services/
│   │   ├── auth.py        accounts and sessions
│   │   ├── attempts.py    attempt lifecycle, grading, timer rule, list statistics
│   │   ├── streaks.py     streak rules
│   │   └── profile.py     profile statistics, calendar, latest results
│   ├── templates/         base, passages, passage_start, attempt, result, profile,
│   │                      login, signup, error, plus _macros and _popover
│   └── static/
│       ├── reader.js      tappable Arabic words and the translation popup
│       ├── attempt.js     timer, pause and resume, autosave, the submit check
│       └── forms.js       sends forms marked data-background without a page reload
├── migrations/            Alembic environment and the initial schema
├── tests/                 conftest.py, factories.py and five test files
├── alembic.ini
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## Known limitations

- The first request after 15 idle minutes takes about a minute (Render free plan).
- Tailwind is compiled in the browser from a CDN and logs a "not for production" warning in
  the console.
- There is no password reset and no limit on login attempts, so sign-ups are best kept closed.
- The word popup only links to Google Translate.
- Changing a loaded passage means deleting and re-seeding it, which also deletes its attempts.
- Interface text and error messages are written directly in Russian in the templates and code.
- Local development uses SQLite, which differs from Postgres (time zones, foreign keys, column
  changes). Run the tests against Postgres before larger changes.
- When you are logged out, submitting a form redirects to `/login` with that form's address
  in `next`. After logging in, the browser opens it with GET and gets `405`.

## Roadmap

**2.0** (planned):

- personal content for each user next to common content managed by an admin
- editors in the app for passages and questions, plus YAML import
- a grammar question bank with random practice sessions
- speaking practice: a numbered list of questions with a countdown timer
- a question navigator with a grid of question numbers and review flags
- the interface in Uzbek, Russian and English
- word translation inside the popup (glossary, cache, MyMemory)
- Postgres in Docker for local development, and code organised by feature
