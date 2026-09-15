# AI Coding Assistant — Phases 0–11

This is the full feature set from the original spec, built end-to-end:
project scaffolding, the complete data layer, a working multi-user auth
system, an enforced and tested multi-user data-isolation contract, a
full project/file management UI, a real Monaco-based code editor, a
provider-agnostic AI architecture with working Gemini key rotation, AI
chat with context selection, all seven code-intelligence features, a
real diff-review UI, a Code Analysis Dashboard, toast notifications and
a command palette, and now CSRF protection plus file-validation
hardening. What's left is the kind of ongoing security review that
never really finishes — see the note at the end of this section.

**Other project docs**: [`PRD.md`](PRD.md) (product requirements — the
higher-level "what and why"), [`CHANGELOG.md`](CHANGELOG.md)
(phase-by-phase history), [`SECURITY.md`](SECURITY.md) (security policy
and the current hardening checklist), [`CONTRIBUTING.md`](CONTRIBUTING.md)
(dev setup and conventions for contributing), [`LICENSE`](LICENSE) (MIT —
replace the placeholder name/email in `LICENSE` and `SECURITY.md` before
publishing this repo publicly).

## What's implemented

- **Phase 0 — Scaffolding**: Flask app factory, React + Vite + Tailwind shell,
  `.env.example` files, dev/test/prod config split.
- **Phase 1 — Data layer**: every model from the spec, with foreign keys,
  indexes, and cascading deletes.
- **Phase 2 — Auth**: registration, login/logout, email verification
  (+ resend), forgot/reset password, change password, secure password
  hashing, rate limiting, session cookies.
- **Phase 3 — Multi-user isolation**: a reusable ownership-enforcement
  pattern, backed by isolation tests every new route has had to keep passing.
- **Phase 4 — Project & file management**: full project CRUD with search,
  file CRUD with virtual folders, a working dashboard + project workspace UI.
- **Phase 5 — Code editor**: Monaco Editor with a language selector,
  Format, Copy, Clear, dark theme, line numbers, Ctrl/Cmd+S.
- **Phase 6 — AI provider architecture**: `AIService`, a provider-agnostic
  interface, a working `GeminiProvider` with multi-key rotation, and stub
  Groq/OpenRouter/Claude providers.
- **Phase 7 — AI chat**: a chat panel backed by real `Conversation`/
  `Message` persistence, controlled context selection, auto-titling,
  regenerate, "Ask about selection →".
- **Phase 8 — Code-intelligence features**: Explain, Generate, Debug,
  Review, Optimize, Tests, Documentation — all built on `AIService` and
  shared prompt templates, with defensive parsing of AI responses.
- **Phase 9 — Diff/apply UI + Code Analysis Dashboard**: AI-suggested
  code changes open a real Monaco `DiffEditor` with explicit Accept/
  Reject; a Code Analysis Dashboard aggregates `CodeAnalysis` scores,
  complexity, and issue history per project.
- **Phase 10 — UI polish**: toast notifications, shared empty/loading
  states, and a global command palette (`Ctrl/Cmd+K`).
- **Phase 11 — Security hardening**: **CSRF protection** via a
  double-submit cookie (`utils/csrf.py`) — every authenticated,
  state-changing request now requires an `X-CSRF-Token` header matching
  a cookie set at login, which a cross-site attacker's page can trigger
  but can't read; the previously-unused `ALLOWED_FILE_EXTENSIONS`
  allowlist from Phase 0's config is now actually enforced on file
  create/rename, alongside new filename/folder-path checks that reject
  path-traversal segments (`..`), null bytes, and path separators; a
  full route-by-route audit confirmed every mutating endpoint has both
  `@login_required` and the appropriate rate limit; and a test now
  covers the previously-implicit assumption that a tampered session
  cookie degrades to "logged out" rather than crashing or, worse, being
  accepted. 28 new tests (10 CSRF, 17 file validation, 1 session
  tampering) bring the suite to 132.

**Ongoing, not "done"**: security hardening isn't a phase you finish —
Phase 11 closed the specific, concrete gaps found in a real audit (an
unused allowlist, no CSRF protection, an untested session-tampering
assumption) rather than performing a generic pass with no findings.
Further review — dependency vulnerability scanning, a professional
penetration test, production secrets management — is standard practice
before a real deployment and is out of scope for what a single
development pass can credibly claim to cover. The final project README/
architecture-diagram deliverable the original spec calls for as its own
step is what this file is standing in for so far.

**Backend restructure**: the backend was flattened after Phase 9 — no
more nested `app/` package or separate `run.py`. Everything now lives in
top-level packages (`models/`, `routes/`, `services/`, `utils/`) next to
a single `app.py`, which you run directly with `python app.py`. See
Project structure below for the full layout and why.

## The isolation contract (Phase 3, extended in Phase 4)

Two rules, enforced in one place (`utils/ownership.py`) so every
route — present and future — inherits them automatically:

1. **The owning user id always comes from the session** (`current_user`),
   never from the request body, query string, or URL. A client can send
   any `user_id` it wants in a payload; it's ignored on write, and it's
   never used to decide what's visible on read.
2. **A resource that exists but belongs to someone else returns the same
   404 as a resource that doesn't exist.** We never return 403 for this
   case — that would confirm the id is valid and just owned by someone
   else, which is itself a (small) information leak.

`get_owned_or_404(Model, id)` and `owned_query(Model)` are the two
helpers every route uses instead of `Model.query.get(id)` /
`Model.query.all()`. Files add a second check on top: a file must belong
to both the current user *and* the project named in the URL, so a valid
file id can't be probed for existence by guessing project ids you do own.

17 tests in `tests/test_isolation.py` cover: cross-user read/rename/
delete on projects, files, and conversations; list endpoints never
leaking another user's rows; nonexistent vs. someone-else's-resource
both returning 404; unauthenticated access returning 401; and a
client trying to spoof `user_id` on creation being ignored. Phase 4
adds 3 more isolation cases in `tests/test_projects_files.py` covering
the new file-update, folder-rename, and project-search endpoints.

## Folders (Phase 4)

There's no separate Folder table — a folder is just the set of files
sharing a `folder_path` prefix (e.g. `"src/utils"`), same as how git
itself has no concept of empty directories. Practically this means:

- Folders appear in the explorer only while they contain at least one file.
- Renaming a folder (`PATCH /api/projects/<id>/folders`) bulk-rewrites
  `folder_path` on every file under it, including nested subfolders.
- Creating a "new folder" happens implicitly the first time you create a
  file inside it — there's no standalone "create empty folder" action in
  the UI for this reason.

## The code editor (Phase 5)

- Built on [`@monaco-editor/react`](https://github.com/suren-atoyan/monaco-react),
  the same editor VS Code uses.
- **By default it loads the Monaco runtime from a CDN at browser runtime**
  (this is `@monaco-editor/react`'s default `loader` behavior) — so the
  editor needs internet access the first time it loads in a session, even
  though the app itself runs fully locally. If you need a fully offline
  setup, switch to self-hosting Monaco's assets via the `loader.config()`
  API and add `monaco-editor` as an explicit dependency — not done here
  to keep the Phase 5 footprint small.
- Language changes in the editor toolbar persist immediately (a `PATCH`
  to the file, same as a folder rename) since it's metadata, not file
  content — unlike edits to the code itself, which stay in a "dirty"
  draft state until you hit **Save** or **Ctrl/Cmd+S**.
- **Format** only does something for languages Monaco ships a built-in
  formatter for (JS/TS/JSON/HTML/CSS) — it's disabled with an explanatory
  tooltip everywhere else, rather than silently doing nothing.
- **Analyze** is present but disabled — it's a placeholder for the AI
  code-review/optimization features that land in a later phase, not
  functionality that's cut.

## AI provider architecture (Phase 6)

`services/ai/` is the whole abstraction layer:

```
AIService (service.py)
   │  — the ONLY thing routes/chat/code-review should import from here
   │
   ├── GeminiProvider   (gemini.py)   — implemented, with key rotation
   ├── GroqProvider     (groq.py)     — stub
   ├── OpenRouterProvider (openrouter.py) — stub
   └── ClaudeProvider   (claude.py)   — stub
```

**Key rotation rule** (`GeminiProvider.generate`): on a 429 (rate limit),
401/403 (invalid/rejected key), 5xx (transient provider error), or a
network-level failure, it tries the next configured key. On an ordinary
400 (bad request — e.g. an empty prompt), it does **not** rotate, since
every key would fail identically and burning through all of them wastes
quota for no benefit. Once a key succeeds, it's "sticky" — the next call
tries that key first rather than restarting from key 1 and re-triggering
whichever key is already exhausted.

**Adding a real provider later** (Groq, OpenRouter, Claude): fill in
`_call()` in the matching stub file following `gemini.py`'s pattern, add
its API key to `config.py`/`.env.example` (already scaffolded), and
register it in `AIService._build_providers()`. Nothing in routes, chat,
or the code-intelligence features needs to change — they all call
`AIService.generate()`, never a provider directly.

**Testing note**: `tests/test_ai_gemini_provider.py` mocks `requests.post`
rather than calling the real Gemini API — this environment has no
network egress to Google's API, and mocking is also just the right way
to test rotation logic deterministically (you need to control exactly
which status code each key "returns" on each call, which a real flaky
network call can't guarantee). If you want to sanity-check the real
integration once you have actual Gemini keys, the quickest way is
`GET /api/ai/providers` after setting `GEMINI_API_KEY_1` in `.env` — it
should report `"configured": true` for `gemini`.

## AI chat (Phase 7)

**Context selection** (`services/chat/chat_context.py`) is capped on
purpose, per the spec's "don't send the whole project" requirement:

- Up to the last **10 messages** of conversation history
- The **current file's content**, truncated at 6,000 characters, if the
  "include current file" checkbox is on
- A **selected code snippet**, truncated at 4,000 characters, if sent
  from the editor's "Ask about selection →" button — this takes
  precedence as the more specific signal when both are present

A file offered as context is checked against the conversation's
`project_id` — a file from a different project is silently dropped
rather than leaked into the prompt (covered by
`test_file_from_different_project_is_ignored_as_context`).

**Failure handling**: the user's message is persisted *before* the AI
call runs, so a provider outage (`AIProviderUnavailable` → 503) or a
genuine request error (`AIProviderError` → 502) never loses what they
typed — only the assistant's reply is missing, and the error message
says so.

**Regenerate** replaces the assistant message's content in place
(same row, rebuilt from the same preceding context) rather than
appending a duplicate — matches what "regenerate" means to someone
looking at the thread.

**Auto-titling**: a new conversation named "New conversation" takes its
title from the first user message (truncated to 60 chars) the first
time a message is sent — subsequent messages never overwrite it.

## Code-intelligence features (Phase 8)

All seven live under `/api/code/*` and share the same source-resolution
helper (`resolve_source` in `services/code/common.py`, called from `api/code.py`): pass `code` directly,
or `file_id` to load it from an owned file (draft/unsaved editor content
is what the frontend actually sends, via the explicit `code` field —
not what's persisted to the file — so analysis reflects what's on
screen, not what was last saved).

| Feature | Persists to | Notes |
|---|---|---|
| Explain | — (ephemeral) | Free-text, covers all the facets from the spec in one response |
| Generate | — (ephemeral) | Description → code; JSON output with a raw-text fallback if the model doesn't comply |
| Debug | — (ephemeral) | Always labeled a suggestion (`is_suggestion: true`), never a guaranteed fix |
| Review | `CodeReview` + `CodeAnalysis` | Severity-tagged findings (Critical/High/Medium/Low/Suggestion) + 0–100 scores |
| Optimize | — (ephemeral) | Returns `original_code` and `optimized_code` for a side-by-side view |
| Tests | `GeneratedTest` | Framework-aware (pytest/unittest/jest/mocha/junit); response is stripped of any surrounding prose/fences before saving |
| Documentation | `Document` | `doc_type` selects docstrings/comments/README section/API docs |

**Why some persist and some don't**: the Phase 1 schema only has tables
for `CodeReview`, `CodeAnalysis`, `GeneratedTest`, and `Document` —
explain/generate/debug/optimize have no dedicated table, same as a
one-off chat reply. If you want history for those later, the pattern to
follow is already established by review/tests/documentation.

**Every response is defensively parsed.** The prompts ask for JSON (or a
single fenced code block), but the parsing (`services/ai/parsing.py`)
never trusts the model to comply — a malformed response falls back to a
best-effort extraction rather than a 500. `test_review_falls_back_to_
single_finding_on_bad_json` and the equivalent tests for generate/debug
lock this in.

**Isolation extends here too**: a `file_id` must belong to the caller,
and a `project_id` passed without a file is checked against project
ownership before a review/test/doc can attach to it — otherwise a
client could get a persisted row pointing at someone else's project.

## Diff/apply UI and the Analysis Dashboard (Phase 9)

**Diff review**: Optimize, Debug (its `corrected_code`), and Generate's
"Apply to editor"/"Insert into editor" buttons no longer write to the
draft directly. They open `DiffReviewModal`, which renders Monaco's
`DiffEditor` (read-only, side-by-side) comparing the current draft
against the AI's suggestion. Only clicking **Accept** applies it —
marking the file dirty, same as any manual edit, so **Save** is still a
separate step. **Reject** discards the suggestion with no side effects.

**Code Analysis Dashboard** (`GET /api/projects/<id>/analysis`, opened
via the **📊 Code Analysis** button in the workspace header):

- Latest quality/security/performance/maintainability scores (0–100),
  always labeled an AI-assisted estimate, never a certification
- The complexity summary from the most recent review
- Issues-found count and a severity breakdown (Critical/High/Medium/
  Low/Suggestion) from the most recent review
- A quality-score trend across the last 10 reviews (a plain CSS
  sparkline — no charting library added for one small visual)
- A browsable list of past reviews (`GET /api/projects/<id>/reviews`),
  each expandable to its full findings

Two more read-only history endpoints round out the "Project can contain
Code Reviews / Generated Tests / Documentation" structure from the
spec: `GET /api/projects/<id>/tests` and `GET /api/projects/<id>/documents`
(each with a `/…/<item_id>` detail route for the full content — list
views omit the full code/content to keep payloads small, same pattern
as `ProjectFile.to_dict()` from Phase 4).

**A real bug caught while wiring this up**: the review route's fallback
branch (when the model's JSON doesn't parse) referenced a variable that
only existed in the success branch — `complexity_summary=parsed.get
(...)` outside the `try`, which would have raised `NameError` the first
time a review response failed to parse as JSON. Fixed by computing
`complexity` explicitly in both branches before it's used. Worth
mentioning because it's exactly the kind of bug that survives casual
manual testing (happy-path JSON always parses) and only shows up when
something with real traffic eventually gets a malformed response.

## UI polish (Phase 10)

**Toasts** (`context/ToastContext.jsx`): `useToast()` gives `.success()`,
`.error()`, `.info()` — small, auto-dismissing, stacked bottom-right.
Form-level validation errors (a bad project name, a weak password) stay
as inline field errors right next to the input, since that's genuinely
the better UX for "fix this specific thing" feedback; toasts are for the
"did the thing I clicked actually work" feedback that was previously
silent or buried in a page-level error banner — save, create, rename,
delete, folder rename, and applying an AI diff all surface one now.

**Shared `EmptyState`/`Spinner`** replace the mix of bare "Loading…"
text and ad hoc empty `<div>`s that had accumulated across the dashboard,
workspace, and chat panel — same visual language everywhere now, with
`EmptyState` also carrying a relevant action button (e.g. "+ New file"
when no file is open) instead of just describing the empty state.

**Command palette** (`Ctrl/Cmd+K`, `components/CommandPalette.jsx`):
mounted once at the app root so it's available from any authenticated
page. Type to fuzzy-filter your projects, arrow keys + Enter to jump to
one, or type a name that doesn't match anything and hit Enter to create
it on the spot. It's intentionally scoped to project search/jump/create
for now — it's mounted above the router, so it doesn't have access to a
specific project's local file list; a natural Phase 10 follow-up would
be a project-scoped "quick open file" (e.g. `Ctrl/Cmd+P`) living inside
`ProjectWorkspace` itself, where that file list already exists.

## Security hardening (Phase 11)

**CSRF protection** (`utils/csrf.py`): a double-submit cookie, not
Flask-WTF — this is a JSON API consumed by a React SPA over `fetch`, and
the natural fit for that is a token in a *readable* cookie the frontend
echoes back in a header, not a token embedded in an HTML form. Login
sets a fresh random token in a non-HttpOnly `csrf_token` cookie; every
authenticated `POST`/`PUT`/`PATCH`/`DELETE` to `/api/*` must carry an
`X-CSRF-Token` header matching it, checked with `hmac.compare_digest`
(constant-time, so a timing side-channel can't leak the value
byte-by-byte). A cross-site attacker's page can make the browser send a
request with the victim's cookies attached — that's the entire CSRF
threat model — but it **cannot read** those cookies to construct a
matching header, since browsers enforce same-origin cookie access.
Endpoints reachable before any session exists (register, login, forgot/
reset password, email verification) are exempt: there's no authenticated
session yet for a forged request to ride. `TestingConfig` sets
`WTF_CSRF_ENABLED = False` (that flag already existed, unused, since
Phase 0) so the other 122 tests didn't need to change; a dedicated
`tests/test_csrf.py` builds its own app instance with it back on to
verify the protection itself.

**File validation** (`utils/validation.py`): three real gaps closed, not
generic hardening —

1. `ALLOWED_FILE_EXTENSIONS` was defined in `config.py` since Phase 0 and
   never actually checked anywhere. It's now enforced on file create and
   rename (`Dockerfile`/`Makefile`/etc. are allowed via a small
   extensionless-name allowlist rather than blocking every file with no
   dot in its name).
2. Filenames and folder paths could previously contain `..` segments,
   null bytes, or path separators — harmless today since they're plain
   string columns with no filesystem access behind them, but exactly the
   kind of value that becomes dangerous the moment a future feature
   (project export, a zip download) touches a real filesystem. Rejected
   at the API boundary now rather than trusted downstream.
3. A route-by-route audit (every blueprint, comparing route count
   against `@login_required` count) confirmed no endpoint was
   accidentally left unprotected, and a second pass over every mutating
   route confirmed rate-limit coverage matches the actual risk (account
   creation, login, email-sending, and AI-cost-bearing endpoints are all
   limited; cheap authenticated CRUD on your own resources isn't, which
   is a deliberate choice, not a gap).

**Session tampering**: added a test asserting a forged/corrupted session
cookie degrades to "not logged in" (`401`) rather than crashing the
request — Flask's signed-cookie verification already guaranteed this,
but it was previously an implicit assumption rather than a checked one.

## Project structure

The project was restructured twice after Phase 9: first flattening the
backend's nested `app/` package into a single `app.py` entry point
(Phase 11-era), then again into the unified layout below — `src/` and
`server/` living side by side at the project root, no `frontend/`/
`backend/` wrapper folders. `python app.py`, `flask run`, and
`gunicorn app:app` all find the module-level `app` object in
`server/app.py`; imports on the backend stay short (`from models.user
import User`, not `from backend.app.models.user import User`).

```
ai-coding-assistant/
├── src/                        # Frontend (React + Vite + Tailwind)
│   ├── main.jsx, App.jsx, index.css
│   ├── assets/                  # static assets (none yet — see assets/README.md)
│   ├── components/
│   │   ├── common/               # Modal, Spinner, EmptyState, Toast
│   │   ├── auth/                 # AuthShell, ProtectedRoute
│   │   ├── chat/                 # ChatPanel, ChatMessageContent, AiProviderBadge, CommandPalette
│   │   ├── code/                 # CodeEditor, ProjectExplorer, DiffReviewModal, AiActionsModal
│   │   └── analysis/             # CodeAnalysisDisplay (shared ScoreBar/FindingsList), AnalysisDashboardModal
│   ├── pages/
│   │   ├── auth/                 # Login, Register, ForgotPassword, ResetPassword, VerifyEmail, ResendVerification
│   │   ├── Dashboard.jsx, ProjectWorkspace.jsx
│   ├── context/                 # AuthContext, ToastContext
│   ├── hooks/                    # reserved — see hooks/README.md
│   ├── services/api.js          # fetch wrapper for the backend, incl. CSRF header handling
│   └── utils/                    # fileTree.js, monacoLanguage.js
│
├── server/                     # Backend (Flask)
│   ├── app.py                   # entry point: app factory + module-level `app`
│   ├── config.py, extensions.py, requirements.txt
│   ├── api/                      # routes — thin; auth.py, projects.py, conversations.py, ai.py, code.py
│   ├── models/                   # SQLAlchemy models — all with to_dict()
│   ├── services/
│   │   ├── auth/                   # token signing + email sending
│   │   ├── ai/                     # base.py, service.py, prompts.py, parsing.py
│   │   │   └── providers/            # gemini.py (implemented), groq.py, openrouter.py, claude.py (stubs)
│   │   ├── chat/chat_context.py    # controlled context selection for AI chat
│   │   ├── code/                   # common.py, analysis_service.py, review_service.py, generation_service.py
│   │   └── projects/project_service.py
│   ├── utils/                    # ownership.py, csrf.py, validation.py
│   └── tests/                    # 135 passing tests, organized by domain
│       ├── auth/, projects/, ai/, code/, services/
│
├── data/                        # Runtime data (gitignored contents, tracked dirs)
│   ├── database/                  # SQLite file lives here (data/database/app.db)
│   ├── uploads/, projects/         # reserved for future features, unused today
│
├── migrations/                  # currently just documents the db.create_all()
│                                  # approach — see migrations/README.md
│
├── scripts/                     # setup.py, seed.py, cleanup.py — see docs/development/setup.md
│
├── docs/
│   ├── architecture/overview.md
│   ├── api/README.md             # endpoint reference generated from server/api/*.py
│   └── development/setup.md
│
├── package.json, vite.config.js, tailwind.config.js, postcss.config.js, index.html
├── .env.example                 # single unified env file for both frontend and backend
├── README.md, PRD.md, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md, LICENSE, .gitignore
```

## Running it locally

### The one-command way (recommended)

```bash
pip install -r server/requirements.txt   # once
cp .env.example .env                      # once — .env lives at the project root
python app.py
```

That's it — `app.py` at the **project root** (not `server/app.py`)
builds the frontend automatically on first run (`npm install` +
`npm run build`, only if `dist/` doesn't exist yet) and then starts
**one Flask process on `http://localhost:5000` serving both the API
and the built React app**. No `cd` into any folder, no separate
frontend dev server to keep running in another terminal.

- First run: prints the npm install/build output, then starts.
- Every run after that: skips straight to starting (it only rebuilds
  if `dist/index.html` is missing — see "Developing with hot reload"
  below for when you *do* want it to rebuild on every change).
- SQLite database is created automatically at `data/database/app.db`.
- Needs Node.js/npm on your `PATH` for that one-time build step —
  everything else is pure Python from that point on.

By default `MAIL_SUPPRESS_SEND=true`, so verification/reset emails are
logged to the console instead of actually sent — convenient for local
dev without SMTP credentials. Set real `MAIL_*` values in `.env` and
flip that flag to `false` to send real email.

### Developing with hot reload

The single-command mode above serves a **static build** of the
frontend — perfect for just running the app, but you won't see changes
to `src/` until you rebuild. While actively working on the frontend,
run the two dev servers separately instead, same as before:

```bash
# terminal 1 — backend only
cd server && python app.py

# terminal 2 — frontend with hot reload, from the project root
npm run dev
```

Vite's dev server (`http://localhost:5173`) proxies `/api/*` to the
Flask backend on `:5000` (see `vite.config.js`) and hot-reloads on
every save. Once you're done and want the single-command mode serving
your latest changes again, just run `npm run build` (or delete `dist/`
and re-run `python app.py` from the root, which rebuilds it for you).

### Tests

```bash
cd server
python -m pytest tests/ -v
```

This runs 135 tests: 17 auth, 20 multi-user isolation, 10 project/file/
folder, 18 AI provider layer, 13 AI chat, 18 code-intelligence features,
9 analysis dashboard/project history, 10 CSRF, 17 file/path validation,
and 3 direct service-layer unit tests (`tests/services/` — calling
service functions directly, no HTTP round-trip, the payoff of having
pulled business logic out of the route handlers).

### Or, the scripted shortcut for first-time setup

```bash
python scripts/setup.py     # creates .env, data/ dirs
python scripts/seed.py      # optional: demo@example.com / DemoPass123!
python app.py
```

See `docs/development/setup.md` for the full walkthrough.

## Trying the auth flow end-to-end

1. Register at `/register`.
2. Since `MAIL_SUPPRESS_SEND` is on by default, check the **backend
   console output** for the verification link (logged as
   `[email suppressed] ...`) instead of your inbox.
3. Open that link (`/verify-email?token=...`) to activate the account.
4. Log in at `/login` — you'll land on the dashboard.
5. Try `/forgot-password` → check the console for the reset link →
   `/reset-password?token=...`.

## Auth security notes

- Login/forgot-password/resend-verification all return generic,
  identically-shaped responses regardless of whether the email exists,
  to avoid account enumeration.
- Verification and reset tokens are signed (`itsdangerous`), single-use
  (tracked in the DB and marked `used_at` on consumption), and
  time-limited (24h / 1h respectively).
- Passwords are hashed with Werkzeug's `generate_password_hash`
  (PBKDF2), never stored or logged in plaintext.
- Sensitive auth endpoints are rate-limited (Flask-Limiter).
- Unhandled server errors are logged internally but return a generic
  message to the client — no stack traces are ever exposed.
- See **Security hardening (Phase 11)** above for CSRF protection and
  file/path validation added after this initial auth work.

## Trying the project/file UI (Phase 4)

1. Log in, then click **+ New project** on the dashboard.
2. Open the project — you land in the workspace with an empty file
   explorer on the left.
3. Click **+ New file**, give it a name (optionally a folder path like
   `src/utils`), pick a language, and it opens in the (plain-text, for
   now) editor on the right.
4. Edit content and click **Save** — it persists via `PATCH
   /api/projects/<id>/files/<id>`.
5. Hover a folder in the explorer to rename it (moves every file inside);
   use the file header's **Delete file** to remove a file; use the
   dashboard's **Rename**/**Delete** on a project card for project-level
   changes.

## Trying the AI chat (Phase 7)

Chat won't actually produce responses without a real Gemini key — set
`GEMINI_API_KEY_1` in `.env` first (see Phase 6 above for how to verify
it's picked up via `GET /api/ai/providers`). With that in place:

1. Open a project, click **+ New chat** in the right-hand panel.
2. Ask something — with a file open, the "Include current file" checkbox
   attaches it as context automatically.
3. Highlight code in the editor and click **Ask about selection →** in
   the toolbar — it opens (or reuses) a chat and attaches the selection.
4. Hover **↻ Regenerate** under any assistant reply to try again with
   the same context.

Without a Gemini key configured, sending a message will save your
message and then show "The AI assistant is temporarily unavailable" —
that's the intended failure path, not a bug (see `test_user_message_
persisted_even_if_ai_call_fails`).

## Trying the code-intelligence features (Phase 8)

Same prerequisite as chat — set `GEMINI_API_KEY_1` in `.env` first.

1. Open a file in the workspace and click **Analyze ✨** in the editor toolbar.
2. **Explain**/**Review** just need a click — they run on whatever's
   currently in the editor (including unsaved changes).
3. **Optimize**/**Debug**/**Generate** offer an **Apply to editor** button
   once they return a result — this overwrites the draft directly (no
   diff view yet, that's Phase 9) and marks the file dirty, so **Save**
   is still a separate, deliberate step.
4. **Tests** offers **Save as new file** (`test_<filename>` in the same
   folder); **Documentation** just displays its output for now — wiring
   that into a docs tab/section is part of Phase 9's UI work.

## Trying the diff UI and dashboard (Phase 9)

1. With a Gemini key configured, open **Analyze ✨** → **Optimize** (or
   **Debug**/**Generate**) and get a suggestion.
2. Click **Apply to editor** (or **Insert into editor**) — instead of
   overwriting immediately, it now opens a diff view. Review it, then
   **Accept** (applies, marks the file dirty) or **Reject** (discards,
   nothing changes).
3. Click **📊 Code Analysis** in the header — empty until you've run at
   least one **Review**. Run one from the Analyze menu, then reopen the
   dashboard to see scores, complexity, and the issue breakdown; run a
   few more over time to see the quality-trend sparkline populate.

## Trying the UI polish (Phase 10)

1. Press **⌘K** / **Ctrl+K** from the dashboard or inside a project —
   type to filter your projects, ↑↓ + Enter to jump to one, or type a
   name nothing matches and hit Enter to create it.
2. Save a file, rename a folder, or delete a project — each now shows a
   toast in the bottom-right instead of (or in addition to) an inline
   message.
3. Open a project with no files yet, or search for a project name that
   doesn't exist — both now show a consistent empty-state card instead
   of a bare "no results" line.

## Trying the security hardening (Phase 11)

1. **CSRF**: log in via the actual app (not curl) and try a mutating
   action normally — it works transparently, since `api.js` reads the
   `csrf_token` cookie and attaches it automatically. To see the
   protection itself, open dev tools → Application → Cookies, delete
   `csrf_token` only (leave the session cookie), then try saving a file —
   you'll get a 403.
2. **File validation**: try creating a file named `../evil.py` or one
   ending in `.exe` — both are now rejected with a 400 and a clear
   `field_errors` reason instead of silently succeeding.
3. `Dockerfile`, `Makefile`, `README`, and a few other common
   extensionless names still work — the allowlist isn't just "must have
   a dot".

## Project status

The full feature list from the original spec (sections 1–21) is built,
tested, and running. There's no more "next phase" in the original
20-step plan — what would come next in a real project isn't another
numbered phase but ongoing practices: dependency vulnerability scanning
(`pip-audit`, `npm audit`), a professional security review before
production traffic, monitoring/alerting once deployed, and expanding
provider support (Groq/OpenRouter/Claude) from the stubs in
`services/ai/` as real usage creates demand for them.
