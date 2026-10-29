# Roadmap

What may come after 2.0. Code rules and conventions are in [CONVENTIONS.md](CONVENTIONS.md);
what each release changed is in [CHANGELOG.md](../CHANGELOG.md). The plan 2.0 was built
from, with its decisions, is
[ROADMAP-v2.md at v2.0.0](https://github.com/atamuratov07/qiraa/blob/v2.0.0/docs/ROADMAP-v2.md).

## Ideas

- **Speaking practice**, the plan so far:

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

- **Translations written with the content**, for passages. Their files are written by a
  chatbot from the import prompt, and the same model can translate the passage in context,
  faster and more precisely than MyMemory word by word. This brings back the glossary that
  2.0 dropped: its cost was writing it by hand, which the prompt now does. The plan so far:

  - `translation_ru` becomes `translation`, one text per interface language
    (`{"uz": …, "ru": …, "en": …}`), and the result page shows the reader's language. A
    data migration turns each `translation_ru` into `{"ru": …}`, in passages and in the
    copies attempts keep;
  - a `glossary` with a meaning for every word of the text in the three languages, keyed by
    the word exactly as written (vowel marks kept, punctuation stripped as `reader.js`
    does), so a tap is a plain lookup with no normalising;
  - the prompt asks for the meaning each word has in its sentence, and the import checks
    that every key occurs in the text;
  - attempts copy both with the rest (rule 15), so the popup reads the glossary from the
    page and sends no request;
  - MyMemory stays for what the glossary lacks: selected phrases, grammar questions, and
    passages made in the editor, where three meanings per word are too much to type.

- A translation endpoint on the server, if a provider with a key is needed (meanings in
  context from a language model, a dictionary API, more quota than MyMemory's free one).
  Keys can't be sent to the browser, so the popup would then ask our server.
- **Accounts with an email**, the plan so far:

  - `users.email`, unique ignoring case; nullable at first, so existing accounts keep
    working and add theirs from the profile;
  - sign-up asks for the email and confirms it with a link;
  - "forgot username" mails the username; "forgot password" mails a link to set a new one;
  - one table of tokens for confirmation and password reset, stored hashed like session
    tokens, expiring and single-use;
  - a mail service with a free tier (Resend, Brevo) and a domain of our own with SPF and
    DKIM records, since a `*.onrender.com` address can't be a verified sender;
  - emails are never sent to other services, MyMemory included.

  It changes sign-up, so it fits together with personal invite codes.

- Personal single-use invite codes (an `invites` table created from the command line) instead
  of one shared `SIGNUP_CODE`.
- Users publishing their own content as common: one way only (after publishing, only an admin
  can unpublish or delete), since other users' results depend on it. The `is_common` column
  already allows it without a migration.

## Hardening

What a production app of this kind still lacks.

- A limit on login attempts, per username and per address, so passwords can't be guessed at
  speed.
- Error tracking (Sentry or similar), so a failure in production is seen without reading
  Render's logs.
- Security headers: a Content-Security-Policy (scripts from jsdelivr, `connect-src` for
  MyMemory), `X-Content-Type-Options`, `Referrer-Policy` and HSTS.
- Exact versions for everything fetched at run or build time. `@tailwindcss/browser@4` and
  `ghcr.io/astral-sh/uv:latest` follow new releases by themselves, so an upstream release
  can change production without a commit.
- Tailwind compiled when the image is built (the standalone CLI in the `Dockerfile`), in
  place of the browser build and its console warning. It is the project's first build step.
- Browser tests in CI (Playwright) for the attempt page, the navigator and the popup, which
  pytest can't reach.
- Scheduled backups: a `pg_dump` of Neon from a GitHub Actions job to private storage,
  beyond Neon's own restore window.
- Dependency updates opened as pull requests (Dependabot).
