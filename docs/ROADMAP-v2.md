# Qiraa 2.0 roadmap

Living plan for version 2.0. Tick steps off as they merge into `v2`. Code rules and project
conventions are in [CONVENTIONS.md](CONVENTIONS.md).

## What 2.0 adds

1. **Personal and common content.** Every passage, grammar question and speaking set is either
   private (only its author sees and edits it) or common (everyone sees it, admins edit it).
   Common content stays when its author deletes their account.
2. **Grammar practice.** Standalone multiple-choice questions, practised as random sessions of
   any size from common and my questions, or only mine.
3. **Speaking practice.** A set of questions shown as one numbered list, with a preparation
   countdown followed by a speaking countdown. No recording, no checking of answers.
4. **Question navigator.** One question at a time, a grid of question numbers (answered,
   current, flagged), previous/next, keyboard shortcuts, a review screen before submitting.
5. **Interface in Uzbek (Latin), Russian and English.** Interface text and error messages only;
   Arabic content is not translated.
6. **Managing content in the app.** Editors for passages, grammar questions and speaking sets;
   YAML import in the app and from the command line.
7. **Word translation** in the popup: passage glossary first, then MyMemory.
8. **Sign-up with an invite code.**

## Decisions already made

| Topic                 | Decision                                                                                                                                                                                                                                        |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Version number        | 2.0.0: existing attempts need a data migration and content management changes                                                                                                                                                                   |
| Branching             | build on `v2`; `main` keeps serving 1.x; merge `main` into `v2` after any fix                                                                                                                                                                   |
| Question tables       | passage questions and grammar questions share `questions`/`options` (`passage_id` is NULL for grammar questions); speaking gets its own table because it has no options or grading                                                              |
| Attempts              | one `attempts` table for passages and grammar sessions; a new `question_ids` list stores which questions an attempt contains and in what order                                                                                                  |
| Passage title         | optional; when missing, show the start of the text                                                                                                                                                                                              |
| Slug                  | only for common passages loaded from YAML (keeps re-imports from duplicating), generated automatically, unique among common passages                                                                                                            |
| Author and visibility | two separate columns on every content table: `owner_id` is the author, `is_common` is who can see it. A row is never private and authorless (CHECK constraint)                                                                                  |
| Ownership rule        | Visible: common or mine. Editable: mine, or common if I am an admin. Admins don't see other users' private content                                                                                                                              |
| Account deletion      | private content is deleted with the account; common content stays with `owner_id` set to NULL (`ON DELETE SET NULL`), so other users keep their results on it                                                                                   |
| Publishing            | only admins set `is_common`                                                                                                                                                                                                                     |
| Admin                 | `users.is_admin`, set from the command line only                                                                                                                                                                                                |
| Sign-ups              | closed to the public: the form asks for one shared invite code (`SIGNUP_CODE`); `ALLOW_SIGNUP=false` still closes sign-up completely                                                                                                            |
| Bulk loading          | YAML in the app (into my area, or common for admins) and `python -m app.cli import file.yaml --owner <username>` / `--common` from the command line                                                                                             |
| Frontend              | stay server-rendered; add Alpine.js (one script tag) for the passage editor and the navigator; no React, no switch to Django                                                                                                                    |
| Passage editor        | Alpine keeps the passage as JSON and posts it; the same Pydantic schema validates the form and YAML                                                                                                                                             |
| Grammar session       | `/grammar` is a start form only (no page that lists the whole bank): pool "common + mine" or "only mine", any size, both remembered in the browser; the size is capped at the number of questions in the pool                                   |
| Speaking timer        | one timer for the whole list: a preparation countdown, then a speaking countdown. Each set stores default `prepare_seconds` and `speak_seconds`; the session page lets me change both before starting and remembers them in the browser per set |
| Word translation      | passage glossary, then MyMemory; no cache table in 2.0                                                                                                                                                                                          |
| Translations          | gettext with Babel and Jinja's i18n extension; English msgids; catalogs for `ru`, `uz`, `en`                                                                                                                                                    |
| Language choice       | user setting, then cookie, then `Accept-Language`, then English                                                                                                                                                                                 |
| Dates                 | Babel's date formatting replaces the hand-written Russian month names                                                                                                                                                                           |
| Local database        | Postgres in Docker Compose for development and tests; the app itself runs on the machine, not in a container; SQLite support removed                                                                                                            |
| Code layout           | organise by feature (see step 2)                                                                                                                                                                                                                |

## Open decisions (likely choice first)

1. Editing content that already has attempts: edit in place (old results show the current
   question) / lock content with attempts.
2. Does finishing a speaking session count for the streak? Leaning yes. The streak itself
   only needs a call to `record_activity()`, but the profile calendar reads
   `attempts.submitted_at`, so it also needs a small `speaking_sessions` table
   (user, set, finished_at). If no, there is no table.

## Data model changes

```
users             + is_admin        bool, default false
                  + locale          str, nullable          "uz" | "ru" | "en"

passages          + owner_id        → users.id, nullable, ON DELETE SET NULL
                  + is_common       bool, default false
                  CHECK: is_common OR owner_id IS NOT NULL
                    title           now nullable
                    slug            now nullable; unique WHERE is_common
                    glossary        used by word translation

questions           passage_id      now nullable (NULL = grammar question)
                  + owner_id        → users.id, nullable, ON DELETE SET NULL
                  + is_common       bool, default false
                  CHECK: passage_id IS NULL OR (owner_id IS NULL AND NOT is_common)
                         (a passage question takes author and visibility from its passage)
                  CHECK: passage_id IS NOT NULL OR is_common OR owner_id IS NOT NULL

attempts            passage_id      now nullable (NULL = grammar session)
                  + kind            "passage" | "grammar"
                  + question_ids    JSON list of question ids, in order
                  unique (user_id, passage_id) WHERE open AND kind = 'passage'
                  unique (user_id)            WHERE open AND kind = 'grammar'

speaking_sets     (new) id, owner_id → users.id nullable ON DELETE SET NULL,
                  is_common, title, questions JSON list[str],
                  prepare_seconds, speak_seconds, created_at
                  CHECK: is_common OR owner_id IS NOT NULL

speaking_sessions (new, only if open decision 2 is yes) id, user_id, set_id, finished_at
```

Migrations:

- The ownership migration adds `is_common` with `server_default` false, then sets
  `is_common = true` on every existing passage (they have no owner yet, so the CHECK needs it).
- The attempts migration fills `kind = 'passage'` and `question_ids` from each attempt's
  passage (a data migration, with a test on a copy of real data).

Account deletion is one service function and one commit: delete my private passages,
grammar questions and speaking sets, then delete the user. The database sets `owner_id` to
NULL on my common content. If the service forgets the first part, the CHECK constraints make
the user delete fail instead of leaving private rows nobody can reach.

## Steps

### 1. Postgres for development and CI

- [x] `docker-compose.yml` with Postgres (same major version as Neon), `qiraa` and
      `qiraa_test` databases.
- [x] GitHub Actions workflow running `uv run pytest` against a Postgres service on every push.
      Done when: `docker compose up -d db`, migrations and all tests pass on Postgres locally and in CI.

### 2. Organise the code by feature

```
app/core/       config, db, templating, i18n, permissions, timeutils, redirects
app/auth/       users, sessions, sign-up/login, deps, security (password and token hashing)
app/practice/   Question, Option, Attempt, AttemptAnswer, attempt service, routes, api,
                attempt/result templates, the question navigator
app/passages/   Passage, list and start pages, editor
app/grammar/    session start page, sessions, editor
app/speaking/   SpeakingSet, session page, editor
app/profile/    statistics, streaks, profile page
app/content/    YAML schemas, import, CLI
app/models.py   imports every model so Alembic sees them
```

Templates stay in `app/templates/<feature>/`.

- [x] Move `core/`, `auth/`, `passages/`, `practice/`, `profile/`; the other folders and
      modules (`grammar/`, `speaking/`, `content/`, `i18n`, `permissions`) arrive with their steps.
      Done when: one commit that only moves code; all tests pass before and after.

### 3. Ownership, admin role, permissions, invite code

- [ ] Migration: `users.is_admin`, `passages.owner_id` (SET NULL), `passages.is_common`
      (existing passages become common), the CHECK, nullable `title`, slug unique
      `WHERE is_common`.
- [ ] `core/permissions.py`: `visible_*()` query filters and `load_visible_*` /
      `load_editable_*` helpers. Routes never call `db.get()` on owned content.
- [ ] Account deletion removes private content first, then the user.
- [ ] `python -m app.cli make-admin <username>`.
- [ ] `SIGNUP_CODE` setting: when set, the sign-up form has a code field, compared with
      `hmac.compare_digest`; a wrong code gives the same kind of form error as a taken username.
- [ ] Parametrised tests: owner / other user / admin × view / edit / delete / practise for
      every content type.
- [ ] Deletion tests: private content is gone; common content stays with no owner; another
      user's attempts on it stay; deleting the user without removing private content first
      fails on the CHECK.
      Done when: the permission and deletion tests pass, another user's private passage is a 404
      everywhere, and sign-up without the code is refused.

### 4. Translation setup

- [ ] Babel + Jinja i18n extension; `_()`/`ngettext` in templates, services and JS strings
      (passed to the page as a small JSON block).
- [ ] Wrap existing pages with English msgids; the `ru` catalog reproduces today's Russian text.
- [ ] Language switch in the header; `users.locale`; cookie for logged-out pages.
- [ ] Error keys instead of finished sentences in `AuthError`, `AttemptClosed`, `BadAnswer`.
      Done when: switching ru ↔ en changes every page; the Russian interface looks as it does in 1.0.

### 5. Content format and import

- [ ] Pydantic schemas for passages, grammar questions and speaking sets (shared by editor,
      YAML and CLI).
- [ ] `python -m app.cli import file.yaml --owner <username> | --common`; `check` command.
- [ ] Move the four real passages from `seed.py` to `content/*.yaml`; decide what to do with
      `skill` (drop it, or add the column).
- [ ] Import page: paste or upload YAML, see errors per line, save to my area (or common for
      admins).
      Done when: re-importing a common file updates it instead of duplicating.

### 6. Passage editor and "Manage" pages

- [ ] `/manage/passages`: list, new, edit, delete; Alpine editor with dynamic questions and
      2–6 options, correct option as a radio, explanation, optional title and translation.
- [ ] Admins get a "Common" checkbox.
      Done when: a passage created in the editor can be practised; validation errors show on the form.

### 7. Attempts no longer tied to a passage

- [ ] Migration: `kind`, `question_ids`, nullable `passage_id`, new partial indexes; data
      migration for existing attempts.
- [ ] Attempt service reads questions through `question_ids`; autosave checks
      `question_id in attempt.question_ids`.
- [ ] Rehearse the migration on a Neon branch of production data.
      Done when: all existing tests pass unchanged in behaviour; old attempts still show their results.

### 8. Grammar practice

- [ ] Migration: `questions.owner_id` (SET NULL), `questions.is_common`, both CHECKs.
- [ ] `/grammar`: start form with pool ("common + mine" / "only mine") and size, showing how
      many questions the pool has; both choices remembered in the browser. The server caps the
      size at the pool count and shows a message when the pool is empty.
- [ ] Sessions use the attempt page without the passage column; results, profile and streak
      include them.
- [ ] `/manage/grammar`: list of my questions (and common ones for admins) with new, edit,
      delete, and YAML import.
      Done when: a 10-question session can be started, autosaved, submitted and reviewed, and asking
      for 50 questions from a pool of 40 gives 40.

### 9. Question navigator

- [ ] One question at a time (passage stays visible beside it; above it on phones).
- [ ] Number grid: current, answered, unanswered, flagged; ←/→, 1–4, F shortcuts; `#q3` in
      the URL; flags kept in the browser per attempt.
- [ ] Review screen before submitting replaces the confirm dialog; result page reuses the grid.
- [ ] Works as a plain list without JavaScript.
      Done when: used by passage attempts, grammar sessions and both result pages.

### 10. Speaking practice

- [ ] `speaking_sets` table with `owner_id` (SET NULL), `is_common` and the CHECK.
- [ ] `/speaking` list, `/speaking/{id}` session page: all questions as one numbered list,
      preparation countdown, then speaking countdown, then a "done" state. Before starting,
      both durations can be changed (defaults from the set, remembered in the browser per set).
- [ ] `/manage/speaking` editor (one question per line, default durations).
- [ ] If open decision 2 is yes: `speaking_sessions` table, `POST /speaking/{id}/finish`
      calls `record_activity()`, and the profile calendar reads both tables.
      Done when: a set can be created and run with both countdowns (and, if decided, counted for the
      streak and shown on the calendar).

### 11. Word translation

- [ ] `/api/translate`: passage glossary, then MyMemory (`MYMEMORY_EMAIL` raises the free
      quota from 5,000 to 50,000 characters a day).
- [ ] Arabic normalisation: strip vowel marks, unify alef forms, try without و/ف/ب/ك/ل/ال prefixes.
      Done when: tapping a glossary word and a new word each return Russian.

### 12. Uzbek and English translations

- [ ] Fill `uz` and `en` catalogs; Uzbek checked by a native speaker.
      Done when: no untranslated msgid in any catalog (`pybabel` reports none).

### 13. Release 2.0.0

- [ ] Take a fresh Neon snapshot; rehearse `alembic upgrade head` on a Neon branch.
- [ ] Set `SIGNUP_CODE` on Render.
- [ ] Update README (settings table: `SIGNUP_CODE`, `MYMEMORY_EMAIL`), CHANGELOG; merge `v2`
      into `main`; tag `v2.0.0`; GitHub release.
- [ ] Check production: log in, old results, each practice type, each language, sign-up with
      and without the code.

## Routes added in 2.0 (draft)

| Area     | Routes                                                                                                       |
| -------- | ------------------------------------------------------------------------------------------------------------ |
| Grammar  | `GET /grammar` (start form), `POST /grammar/sessions` → existing attempt page                                |
| Speaking | `GET /speaking`, `GET /speaking/{id}`, `POST /speaking/{id}/finish` (only if speaking counts for the streak) |
| Manage   | `/manage/{passages,grammar,speaking}` with `new`, `{id}/edit`, `{id}/delete`; `/manage/import`               |
| Settings | `POST /settings/language`                                                                                    |
| API      | `GET /api/translate?q=…&passage_id=…`                                                                        |

## Later (after 2.0)

- Translation cache table, if lookups feel slow or reach MyMemory's daily limit.
- Personal single-use invite codes (an `invites` table created from the command line) instead
  of one shared `SIGNUP_CODE`.
- Users publishing their own content as common: one way only (after publishing, only an admin
  can unpublish or delete), since other users' results depend on it. The `is_common` column
  already allows it without a migration.
