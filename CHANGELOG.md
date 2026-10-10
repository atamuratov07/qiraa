# Changelog

Notable changes to Qiraa, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/): the major number goes up when a release changes
the data in a way that needs a migration of existing records, or changes how content is managed.

## [Unreleased]

Work towards 2.0: personal and common content, in-app editors, a grammar question bank,
speaking practice, a question navigator, and the interface in Uzbek, Russian and English.

## [1.0.0] - 2026-10-10

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

| Date | Commit | Step |
|---|---|---|
| 6 Oct | `337b6d9` | Initial commit: FastAPI app |
| 6 Oct | `5b85599` | Base and error templates |
| 7 Oct | `c0d76e0` | SQLAlchemy models, SQLite for development and Postgres for production |
| 7 Oct | `a72d398` | Custom authentication |
| 8 Oct | `0f8dcde` | Attempts: start, autosave, heartbeat, submit, discard, tests |
| 8 Oct | `4665cc8` | Migrations reset to a single initial schema |
| 8 Oct | `4fba51d` | Profile page, streaks, statistics, account and result deletion, tests |
| 8 Oct | `f0294e2` | Real passages |
| 8 Oct | `6c2decb` | Russian interface |

[Unreleased]: https://github.com/atamuratov07/qiraa/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/atamuratov07/qiraa/releases/tag/v1.0.0
