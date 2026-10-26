# Qiraa 2.0 roadmap

Living plan for version 2.0. Tick steps off as they merge into `v2`. Code rules and project
conventions are in [CONVENTIONS.md](CONVENTIONS.md).

## What 2.0 adds

1. **Personal and common content.** Every passage and grammar question is either
   private (only its author sees and edits it) or common (everyone sees it, admins edit it).
   Common content stays when its author deletes their account.
2. **Grammar practice.** Standalone multiple-choice questions, practised as random sessions of
   any size from common and my questions, or only mine.
3. **Question navigator.** One question at a time, a grid of question numbers (answered,
   current, flagged), previous/next, keyboard shortcuts, a review screen before submitting.
4. **Interface in Uzbek (Latin), Russian and English.** Interface text and error messages only;
   Arabic content is not translated.
5. **Managing content in the app.** Editors for passages and grammar questions;
   YAML import in the app and from the command line. Editing content never changes past
   results.
6. **Word translation** in the popup: an Arabic word or phrase into Uzbek, Russian or
   English, through MyMemory.
7. **Sign-up with an invite code.**

Speaking practice is postponed until after the 2.0 release (see "Later").

## Decisions already made

| Topic                 | Decision                                                                                                                                                                                                                                                                                                                         |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Version number        | 2.0.0: existing attempts need a data migration and content management changes                                                                                                                                                                                                                                                    |
| Branching             | build on `v2`; `main` keeps serving 1.x; merge `main` into `v2` after any fix                                                                                                                                                                                                                                                    |
| Question tables       | passage questions (`passage_questions`, `passage_options`) and grammar questions (`grammar_questions`, `grammar_options`) have their own tables: attempts read their own copy, so nothing joins them                                                                                                                             |
| Attempts              | one `attempts` table for passages and grammar sessions; each attempt keeps a copy of what it shows (`content`: title, text, translation, questions with their options in shuffled order and the correct one marked)                                                                                                              |
| Editing content       | allowed at any time, also after attempts; a result shows the copy its attempt was taken on and keeps its score (no regrading); answers point into the copy, so editing or deleting content never removes a result                                                                                                                |
| Passage title         | optional; when missing, show the start of the text                                                                                                                                                                                                                                                                               |
| Slug                  | required in content files and written by hand (never generated, so fixing a title can't make the next import add a duplicate); unique among common passages and among each owner's private passages; passages made in the editor have none                                                                                       |
| Author and visibility | two separate columns on every content table: `owner_id` is the author, `is_common` is who can see it. A row is never private and authorless (CHECK constraint)                                                                                                                                                                   |
| Ownership rule        | Visible: common or mine. Editable: mine, or common if I am an admin. Admins don't see other users' private content                                                                                                                                                                                                               |
| Account deletion      | private content is deleted with the account; common content stays with `owner_id` set to NULL (`ON DELETE SET NULL`), so other users keep their results on it                                                                                                                                                                    |
| Publishing            | only admins set `is_common`; unpublishing returns a passage to its author, or to the admin when it has none                                                                                                                                                                                                                      |
| Admin                 | `users.is_admin`, set from the command line only                                                                                                                                                                                                                                                                                 |
| Sign-ups              | closed to the public: the form asks for one shared invite code (`SIGNUP_CODE`); `ALLOW_SIGNUP=false` still closes sign-up completely                                                                                                                                                                                             |
| Bulk loading          | one kind per YAML file, each kind with its own import page (`/manage/passages/import`, `/manage/grammar/import`) into my area, or common for admins; `python -m app.cli import file.yaml --owner <username>` / `--common` reads the kind from the file's top key; importing again updates by slug; real content stays out of git |
| Frontend              | stay server-rendered; add Alpine.js (one script tag) for the editors and the navigator; no React, no switch to Django                                                                                                                                                                                                            |
| Passage editor        | Alpine keeps the passage and posts it as JSON in one form field; `PassageIn` validates it as it does YAML, and errors show under their fields                                                                                                                                                                                    |
| Content language      | Arabic or English: content takes its direction from its own text (`dir="auto"`) and Latin letters are set in Inter; no language field, since word translation looks up Arabic words only                                                                                                                                         |
| Grammar session       | `/grammar` is a start form only (no page that lists the whole bank): pool "common + mine" or "only mine", any size, both remembered in the browser; the size is capped at the number of questions in the pool; one open session per user, which the start page offers to continue or discard                                     |
| Word translation      | the popup asks MyMemory from the browser (no server endpoint, so each user has their own anonymous quota), into the language picked in the popup (Uzbek, Russian or English; the interface's by default, remembered in the browser); Arabic text only; the unused `passages.glossary` column is dropped                          |
| Translations          | gettext with Babel and Jinja's i18n extension; English msgids, so English needs no catalog; catalogs for `ru` and `uz`                                                                                                                                                                                                           |
| Language choice       | the `qiraa_lang` cookie (set from `users.locale` at login), then `Accept-Language`, then English                                                                                                                                                                                                                                 |
| Dates                 | Babel's date formatting replaces the hand-written Russian month names                                                                                                                                                                                                                                                            |
| Local database        | Postgres in Docker Compose for development and tests; the app itself runs on the machine, not in a container; SQLite support removed                                                                                                                                                                                             |
| Code layout           | organise by feature (see step 2); each content feature owns its content end to end (CONVENTIONS rule 18)                                                                                                                                                                                                                         |
| Concurrency           | synchronous: `def` routes with a blocking `Session` run in FastAPI's thread pool; no `async` until a feature waits on many outside calls at once                                                                                                                                                                                 |

## Open decisions (likely choice first)

None for 2.0.

## Data model changes

```
users             + is_admin        bool, default false
                  + locale          str, nullable          "uz" | "ru" | "en"

passages          + owner_id        → users.id, nullable, ON DELETE SET NULL
                  + is_common       bool, default false
                  CHECK: is_common OR owner_id IS NOT NULL
                    title           now nullable
                    slug            now nullable; unique WHERE is_common, and
                                    (owner_id, slug) unique WHERE NOT is_common
                  - glossary        never used; word translation needs none (step 10)

passage_questions   renamed from questions; options renamed to passage_options

grammar_questions (new) id, owner_id → users.id nullable ON DELETE SET NULL,
                  is_common, slug, prompt, explanation
                  CHECK: is_common OR owner_id IS NOT NULL
                  slug unique WHERE is_common, and (owner_id, slug) unique WHERE NOT is_common
grammar_options   (new) as passage_options, question_id → grammar_questions.id CASCADE

attempts            passage_id      now nullable (NULL = grammar session),
                                    ON DELETE SET NULL (was CASCADE)
                  + kind            "passage" | "grammar", no default
                  CHECK: kind = 'passage' OR passage_id IS NULL
                  + content         JSON copy of what the attempt shows: title, text,
                                    translation_ru, and the questions with their options
                                    in shuffled order, the correct one marked
                  - option_order    the order is now the order in `content`
                  unique (user_id, passage_id) WHERE open    (NULLs never collide,
                                                              so sessions skip it)
                  unique (user_id)            WHERE open AND kind = 'grammar'

attempt_answers     question_id     no foreign key: ids inside attempts.content
                    option_id       no foreign key: ids inside attempts.content
```

Migrations:

- The ownership migration adds `is_common` with `server_default` true, so every existing
  passage becomes common (they have no owner yet, so the CHECK needs it), then changes the
  default to false.
- The attempts migrations (step 5) fill `content` from each attempt's passage, with the
  options in the order its `option_order` showed them (a data migration, with a test), then
  drop `option_order` and the answers' foreign keys to questions and options. Step 8 adds
  `kind` with the default `'passage'`, which fills the existing attempts, then drops the
  default.

Account deletion is one service function and one commit: delete my private passages
and grammar questions, then delete the user. The database sets `owner_id` to
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
app/practice/   Attempt, AttemptAnswer, what every attempt shares once started (autosave,
                timer, grading), routes, api, attempt/result templates, the navigator
app/passages/   Passage and its questions, starting an attempt, list and start pages,
                file schema, prompt, import, editor
app/grammar/    GrammarQuestion, GrammarOption, starting a session, start page, file
                schema, prompt, import, editor
app/profile/    statistics, streaks, profile page
app/content/    what content files share: question schema, slugs, loader, errors, the
                import pages, CLI
app/models.py   imports every model so Alembic sees them
```

Templates stay in `app/templates/<feature>/`.

- [x] Move `core/`, `auth/`, `passages/`, `practice/`, `profile/`; the other folders and
      modules (`grammar/`, `content/`, `i18n`, `permissions`) arrive with their steps.
      Done when: one commit that only moves code; all tests pass before and after.

### 3. Ownership, admin role, permissions, invite code

- [x] Migration: `users.is_admin`, `passages.owner_id` (SET NULL), `passages.is_common`
      (existing passages become common), the CHECK, nullable `title`, slug unique
      `WHERE is_common`.
- [x] `core/permissions.py`: `visible()` / `editable()` query filters and `load_visible()` /
      `load_editable()` loaders, generic over the `Owned` mixin. Routes never call `db.get()`
      on owned content.
- [x] Account deletion removes private content first, then the user.
- [x] `python -m app.cli make-admin <username>`.
- [x] `SIGNUP_CODE` setting: when set, the sign-up form has a code field, compared with
      `hmac.compare_digest`; a wrong code gives the same kind of form error as a taken username.
- [x] Parametrised tests: owner / other user / admin × view / edit / delete / practise for
      every content type (passages now; route tests for edit and delete come with step 7).
- [x] Deletion tests: private content is gone; common content stays with no owner; another
      user's attempts on it stay; deleting the user without removing private content first
      fails on the CHECK.
      Done when: the permission and deletion tests pass, another user's private passage is a 404
      everywhere, and sign-up without the code is refused.

### 4. Translation setup

- [x] Babel + Jinja i18n extension; `_()`/`ngettext` in templates, services and JS strings
      (passed to the page as a small JSON block).
- [x] Wrap existing pages with English msgids; the `ru` catalog reproduces today's Russian text.
- [x] Language switch in the header; `users.locale`; cookie for logged-out pages.
- [x] Messages are translated where they are raised (the request's language is known there);
      `/api` errors stay English.
- [x] `uz` catalog filled.
      Done when: switching changes every page; the Russian interface reads as in 1.0, except
      dates, which follow CLDR.

### 5. Attempts keep a copy of their content

- [x] Migrations: `content`, with a data migration that builds it for existing attempts;
      then `content` NOT NULL, nullable `passage_id` with `ON DELETE SET NULL`, no
      `option_order`, no foreign keys from `attempt_answers` to questions and options. `kind`
      and the grammar index moved to step 8, where grammar sessions first need them.
- [x] Starting an attempt copies the passage into `content`; the attempt page, grading and the
      result page read the copy; autosave checks that the question and option are in it.
- [x] Deleting a passage keeps everyone's results on it; an unfinished attempt on it can still
      be submitted.
      Done when: all existing tests pass unchanged in behaviour; old attempts still show their
      results; changing or deleting a question after an attempt doesn't change that attempt's
      result page.

### 6. Content format and import

- [x] Pydantic schemas for passages, shared by the editor, YAML and the CLI (grammar and
      the grammar schema came with step 8). Errors carry a type and a line number and
      are translated where they are shown.
- [x] `python -m app.cli import file.yaml --owner <username> | --common`; `check` command.
- [x] Move the four real passages from `seed.py` to a YAML file kept out of git
      (`content/example.yaml` shows the format); `skill` dropped.
- [x] Import page: paste or upload YAML, see errors per line, save to my area (or common for
      admins); a prompt that tells a chatbot how to turn any material into the format.
- [x] Re-importing a passage replaces its questions; results keep their copy.
      Done when: re-importing a common file updates it instead of duplicating.

### 7. Passage editor and "Manage" pages

- [x] `/manage/passages`: list, new, edit, delete; Alpine editor with dynamic questions and
      2–6 options, correct option as a radio, explanation, optional title, translation and
      glossary.
- [x] Admins get a "Common" checkbox.
      Done when: a passage created in the editor can be practised; validation errors show on the form.

### 8. Grammar practice

- [x] Rename `questions`/`options` to `passage_questions`/`passage_options`.
- [x] Migration: `grammar_questions`, `grammar_options`; `attempts.kind` (existing rows
      `'passage'`, then no default) with its CHECKs, and one open grammar session per user.
- [x] Grammar files (`grammar:`, a slug per question) with their own import page, chatbot
      prompt and CLI support.
- [x] Starting a passage attempt moves from `practice/` to `passages/`.
- [x] `/grammar`: start form with pool ("common + mine" / "only mine") and size, showing how
      many questions the pool has; both choices remembered in the browser. The server caps the
      size at the pool count and shows a message when the pool is empty.
- [x] Sessions and passage attempts have their own attempt and result pages on shared layouts
      in `practice/`; results, profile and streak include sessions.
- [x] `/manage/grammar`: list of my questions (and common ones for admins) with new, edit,
      delete and import; `/passages` and `/grammar` link to their manage pages.
      Done when: a 10-question session can be started, autosaved, submitted and reviewed, and asking
      for 50 questions from a pool of 40 gives 40.

### 9. Question navigator

- [x] One question at a time (passage stays visible beside it; above it on phones), with the
      controls in a bar fixed to the bottom of the screen and the timer in the top corner.
- [x] Number grid: current, answered, unanswered, flagged; ←/→, 1–6, F shortcuts; `#q3` in
      the URL; flags kept in the browser per attempt.
- [x] Review screen before submitting replaces the confirm dialog; result page reuses the grid.
- [x] Works as a plain list without JavaScript.
      Done when: used by passage attempts, grammar sessions and both result pages.

### 10. Word translation

- [x] Drop `passages.glossary` (never used): the column, the schema field, the editor's
      rows and the prompt line.
- [x] The popup asks MyMemory itself (`fetch` from `reader.js`; MyMemory allows it with
      `Access-Control-Allow-Origin: *`): Arabic text only, up to 500 characters
      (MyMemory's limit; longer selections get a message), the answers kept for the
      browser session, errors shown with the Google Translate link.
- [x] The popup: uz · ru · en buttons, the interface language by default, the choice kept
      in the browser; the Google Translate link follows it.
      Done when: tapping a word and selecting a phrase each return a translation in the
      language picked.

### 11. Release 2.0.0

- [ ] Take a fresh Neon snapshot; rehearse `alembic upgrade head` on a Neon branch. While the
      migrations run, the 1.x instance may still serve for a few seconds and fail.
- [ ] Set `SIGNUP_CODE` on Render.
- [ ] If the four 1.0 passages are on Neon, make them private to their author
      (`is_common = false`, `owner_id` set) before anyone else signs up. Content imports run
      from the machine with `DATABASE_URL`: `content/` is not in the Docker image.
- [ ] Update README (settings table: `SIGNUP_CODE`; the data model, where
      attempts now keep a copy instead of `option_order`), CHANGELOG; merge `v2`
      into `main`; tag `v2.0.0`; GitHub release.
- [ ] Check production: log in, old results, each practice type, each language, sign-up with
      and without the code.

## Routes added in 2.0 (draft)

| Area     | Routes                                                                             |
| -------- | ---------------------------------------------------------------------------------- |
| Grammar  | `GET /grammar` (start form), `POST /grammar/sessions` → the session's attempt page |
| Manage   | `/manage/{passages,grammar}` with `new`, `{id}/edit`, `{id}/delete`, `import`      |
| Settings | `POST /settings/language`                                                          |

## Later (after 2.0)

- **Speaking practice**, postponed from 2.0 (it was step 10). The plan so far:
  - a set of questions shown as one numbered list, with a preparation countdown followed by
    a speaking countdown; no recording, no checking of answers;
  - one timer for the whole list: the preparation countdown, then the speaking countdown;
  - a `speaking/` feature (rule 18): a `speaking_sets` table (id, `owner_id` → users.id
    nullable ON DELETE SET NULL, `is_common`, title, questions JSON list[str],
    `prepare_seconds`, `speak_seconds`, created_at, CHECK
    `is_common OR owner_id IS NOT NULL`), whose private sets account deletion removes;
  - `/speaking` list, `/speaking/{id}` session page; before starting, both durations can be
    changed (defaults from the set, remembered in the browser per set);
  - `/manage/speaking` editor (one question per line, default durations), and speaking files
    (`speaking:`) with their own import page and chatbot prompt;
  - open question: does finishing a session count for the streak? Leaning yes; the profile
    calendar reads `attempts.submitted_at`, so that needs a `speaking_sessions` table (user,
    set, finished_at) and `POST /speaking/{id}/finish` calling `record_activity()`.

- A translation endpoint on the server, if a provider with a key is needed (meanings in
  context from a language model, a dictionary API, more quota than MyMemory's free one).
  Keys can't be sent to the browser, so the popup would then ask our server.
- A passage glossary (meanings chosen for this passage, in each interface language), if
  MyMemory's word-by-word meanings fall short. The 1.0 `glossary` column was dropped in
  step 10 without ever being used.
- Personal single-use invite codes (an `invites` table created from the command line) instead
  of one shared `SIGNUP_CODE`.
- Users publishing their own content as common: one way only (after publishing, only an admin
  can unpublish or delete), since other users' results depend on it. The `is_common` column
  already allows it without a migration.
