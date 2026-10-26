# Changelog

Notable changes to Qiraa, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/): the major number goes up when a release changes
the data in a way that needs a migration of existing records, or changes how content is managed.

## [Unreleased]

## [2.0.0] - 2026-10-26

Personal and common content managed in the app, grammar practice, a question navigator, word
translation, sign-up with an invite code, and the interface in Uzbek, Russian and English.
Existing attempts are migrated to keep a copy of what they showed, which is why the major
version goes up. The plan and its decisions are in [docs/ROADMAP-v2.md](docs/ROADMAP-v2.md).

### Added

- Interface in Uzbek, Russian and English, with a language switch in the header. A
  logged-in user's choice is saved with the account. Dates and plural forms follow each
  language.
- Private and common content: every passage and grammar question has an author and a
  visibility. Admins, set with `python -m app.cli make-admin`, edit and publish common
  content. Deleting an account removes its private content and keeps common content.
- Sign-up with an invite code (`SIGNUP_CODE`).
- Editors for passages and grammar questions, with manage pages listing my content (and
  common content for admins).
- Content files in YAML, one kind per file, with a slug written by hand for every entry: an
  import page for each kind, with errors by line and a prompt that tells a chatbot how to
  write the format, and the `import` and `check` commands. Importing again updates by slug.
- Grammar practice: random sessions of any size from common and my questions, or only mine,
  one open at a time. Sessions count for the streak and the profile.
- Question navigator on the attempt page: one question at a time, a bar at the bottom of the
  screen with previous and next, a grid of question numbers (answered, current, flagged),
  keyboard shortcuts, the question in the URL (`#q3`), and a review before submitting. The
  result page has the same grid. Without JavaScript the questions are a plain list.
- Word translation in the popup into Uzbek, Russian or English, from MyMemory, for a tapped
  word or a selection of up to 500 characters.
- Content in English as well as Arabic: text takes its direction from its first letter.
- The greeting and the streak in the header.
- Postgres 18 in Docker Compose for development and tests, with a `qiraa` and a `qiraa_test`
  database.
- GitHub Actions on every push: migrations up, `alembic check`, migrations down, then the
  tests, on Postgres 18.

### Changed

- Attempts keep a copy of what they show (`attempts.content`), filled in for existing
  attempts by a data migration. Editing or deleting a passage no longer changes any result,
  and deleting a passage keeps everyone's results on it. `attempts.option_order` is gone.
- Passage titles are optional; a passage without one shows the start of its text.
- The `questions` and `options` tables are now `passage_questions` and `passage_options`.
- The confirm dialog before submitting is replaced by the navigator's review.
- An unfinished attempt shows as a label on its passage card.
- The four 1.0 passages moved from `app/seed.py` to a YAML file kept out of git.
- Code organised by feature: `app/core`, `auth`, `passages`, `grammar`, `content`,
  `practice` and `profile`, with templates in a folder per feature.

### Removed

- SQLite support. Development, tests and production all use Postgres.
- `passages.glossary`, which nothing used. Content files with a `glossary` key no longer
  load.

### Fixed

- Settings are now read from a `.env` file in the project root. Unknown keys in it are
  ignored.
- A form sent while logged out now brings you back to its page after logging in, instead of
  a `405` error.

## [1.0.0]

First release, built from 6 to 8 October 2026.

### Added

- Accounts: sign-up, login, logout and account deletion. Argon2id password hashes, random
  session tokens stored only as SHA-256 hashes, an `HttpOnly` and `SameSite=Lax` session
  cookie, and an `ALLOW_SIGNUP` setting to close registration.
- Passage list grouped by level, with best score, number of tries and unfinished attempts.
- Practice flow: a start card that hides the text, shuffled options kept per attempt,
  autosave of every pick, a server-side timer based on heartbeats, pause after 30 seconds
  away, submit with grading, and a result page with explanations and the Russian translation.
- One open attempt per passage and one correct option per question, both enforced by partial
  unique indexes.
- Discarding an unfinished attempt from the passage list or the paused card.
- Daily streak counted in Tashkent time, shown on the passage list and the profile.
- Profile page: statistics, a 35-day activity calendar, the latest results with a delete
  button, and account deletion.
- Forms that update the page in the background (discard, delete a result).
- Russian interface, including dates and plural forms.
- Four real passages with 24 questions, loaded by `app/seed.py`.
- Tappable Arabic words with a popup linking to Google Translate.
- Deployment: Docker image on Render, Postgres on Neon, migrations applied on every start.
- 88 tests (rules, services, HTTP routes, streaks, profile), runnable on SQLite or Postgres.

### Development log

| Commit    | Step                                                                  |
| --------- | --------------------------------------------------------------------- |
| `337b6d9` | Initial commit: FastAPI app                                           |
| `5b85599` | Base and error templates                                              |
| `c0d76e0` | SQLAlchemy models, SQLite for development and Postgres for production |
| `a72d398` | Custom authentication                                                 |
| `0f8dcde` | Attempts: start, autosave, heartbeat, submit, discard, tests          |
| `4665cc8` | Migrations reset to a single initial schema                           |
| `4fba51d` | Profile page, streaks, statistics, account and result deletion, tests |
| `f0294e2` | Real passages                                                         |
| `6c2decb` | Russian interface                                                     |

[Unreleased]: https://github.com/atamuratov07/qiraa/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/atamuratov07/qiraa/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/atamuratov07/qiraa/releases/tag/v1.0.0
