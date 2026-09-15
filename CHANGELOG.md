# Changelog

All notable changes to this project, organized by build phase. See
`README.md` for full technical detail on any phase below.

## Post-launch: unified project restructure

Full reorganization into a single unified full-stack layout — `src/`
(frontend) and `server/` (backend) side by side at the project root, no
`frontend/`/`backend/` wrapper folders. Behavior, API contracts,
database schema, and all existing functionality preserved exactly;
this was a structural move only, validated by running the full test
suite and a frontend build after every stage rather than once at the end.

- **Frontend**: moved to root-level `src/`; components reorganized by
  domain (`components/{common,auth,chat,code,analysis}/`); auth pages
  grouped under `pages/auth/`; every import path fixed and the build
  re-verified after each group of moves. Extracted the toast rendering
  markup from `ToastContext.jsx` into `components/common/Toast.jsx` — a
  genuine state/presentation split, not a cosmetic move.
- **Backend**: `backend/` → `server/`; `routes/` → `api/` (rename);
  `services/ai/{gemini,groq,openrouter,claude}.py` → `services/ai/providers/`;
  `services/chat_context.py` → `services/chat/chat_context.py`; all
  import paths and `unittest.mock.patch` target strings updated to match.
- **Business logic extracted from routes into services**, per the
  "routes call services, they don't contain logic" requirement:
  `services/code/{common,analysis_service,review_service,generation_service}.py`
  and `services/projects/project_service.py`. `api/code.py` and
  `api/projects.py` are now thin (parse request → call service → return
  result) instead of containing the actual logic inline. Validated in
  isolation (ran the affected test subsets) before moving on, then
  confirmed with the full suite.
- **Tests** reorganized into `tests/{auth,projects,ai,code,services}/`
  by domain, with proper `__init__.py` packaging so `from tests.conftest
  import ...` keeps working unchanged. Added `tests/services/` — direct
  unit tests calling service functions without going through HTTP, the
  concrete payoff of the extraction above.
- **Database location** moved from `server/instance/app.db` to
  `data/database/app.db` — a project-level `data/` directory (with
  `uploads/`, `projects/` reserved for future features) replaces Flask's
  `instance/` convention.
- **New**: `scripts/{setup,seed,cleanup}.py` (all tested and working,
  not placeholders), `migrations/README.md` (documents the current
  `db.create_all()` approach honestly rather than faking Alembic
  scaffolding), `docs/{architecture,api,development}/`.
- Full test suite (135 tests, including 3 new service-layer unit tests)
  passing after every stage; `npm run build` verified from the new root
  location.

## Post-launch: flattened backend entry point (earlier restructure)

Before the unified `src/`+`server/` layout above, an earlier pass
removed the backend's nested `app/` package and separate `run.py`,
consolidating into a single `app.py` entry point with flat top-level
packages. Superseded in place by the restructure above, which moved
that same flat `models/`/`routes/`/`services/`/`utils/` layout from
`backend/` into `server/` and renamed `routes/` to `api/`.

## Phase 11 — Security hardening
- Added CSRF protection via a double-submit cookie (`utils/csrf.py`);
  every authenticated mutating `/api/*` request now requires a matching
  `X-CSRF-Token` header.
- Enforced the `ALLOWED_FILE_EXTENSIONS` allowlist (defined since Phase
  0, previously unused) on file create/rename.
- Added filename/folder-path validation rejecting path traversal (`..`),
  null bytes, and path separators.
- Added a rate limit to the email-verification endpoint for consistency
  with resend-verification.
- Added a test confirming a tampered session cookie degrades to
  "logged out" rather than crashing.
- 28 new tests (132 total).

## Phase 10 — UI polish
- Added a global toast notification system (`ToastContext`/`useToast`).
- Added shared `EmptyState`/`Spinner` components, applied consistently
  across the dashboard, workspace, and chat panel.
- Added a global command palette (`Ctrl/Cmd+K`) for searching, jumping
  to, or creating projects from anywhere in the app.

## Phase 9 — Diff/apply UI + Code Analysis Dashboard
- Replaced direct "Apply to editor" overwrites (from Optimize/Debug/
  Generate) with a real Monaco `DiffEditor` review step requiring
  explicit Accept/Reject.
- Added the Code Analysis Dashboard: latest scores, complexity summary,
  issues-by-severity breakdown, a quality-trend sparkline, and a
  browsable review history.
- Added `to_dict()` to `CodeReview`, `CodeAnalysis`, `GeneratedTest`,
  and `Document` (previously serialized ad hoc).
- Added project-scoped history endpoints: `GET /api/projects/<id>/reviews`,
  `/tests`, `/documents`.
- Fixed a `NameError` in the review route's JSON-parse-failure fallback
  path (a variable referenced outside the scope it was defined in).

## Phase 8 — Code-intelligence features
- Implemented all seven features from the spec: Explain, Generate,
  Debug, Review, Optimize, Tests, Documentation — each its own
  `/api/code/*` route built on shared prompt templates
  (`services/ai/prompts.py`) and defensive response parsing
  (`services/ai/parsing.py`).
- Review and Analysis persist to `CodeReview`/`CodeAnalysis`; Tests and
  Documentation persist to `GeneratedTest`/`Document`.
- Added the "AI Actions" modal (the editor's "Analyze ✨" button) in
  the frontend covering all seven features.

## Phase 7 — AI chat
- Implemented `POST /api/conversations/<id>/messages` and `.../regenerate`,
  wired to `AIService.generate()` with controlled context selection
  (`services/chat_context.py`): current file, an explicit selection, and
  the last 10 messages — never the whole project.
- The user's message is persisted before the AI call runs, so a
  provider outage never loses what they typed.
- Added auto-titling from the first message and a "regenerate" action
  that replaces the assistant's reply in place.
- Added the `ChatPanel` frontend component and "Ask about selection →"
  in the editor toolbar.

## Phase 6 — AI provider architecture
- Introduced `AIService` and the `AIProvider` interface.
- Implemented `GeminiProvider` with multi-key rotation (rotates on rate
  limit/quota/invalid-key/transient-5xx, never on an ordinary bad
  request) and a "sticky" key that stays in use once it succeeds.
- Added stub `GroqProvider`/`OpenRouterProvider`/`ClaudeProvider`.
- Added `GET /api/ai/providers` and a live status badge in the frontend.

## Phase 5 — Code editor
- Integrated Monaco Editor with a language selector, Format (for
  languages with a built-in formatter), Copy, Clear, dark theme, line
  numbers, and Ctrl/Cmd+S.

## Phase 4 — Project & file management
- Full project CRUD with search.
- File CRUD with virtual folders (no separate folder table — derived
  from `folder_path`, same approach git uses for directories), folder
  rename bulk-moving every file under it, duplicate-name and file-size
  validation.
- Built the real dashboard (project grid, search, create/rename/delete)
  and the project workspace (file explorer, content editor).

## Phase 3 — Multi-user isolation
- Introduced the ownership-enforcement pattern (`utils/ownership.py`):
  the authenticated user id always comes from the session, and a
  resource that exists but belongs to someone else returns the same 404
  as one that doesn't exist.
- Added minimal Project/File/Conversation routes to give the pattern
  real endpoints to be tested against, plus 17 isolation tests.

## Phase 2 — Authentication
- Registration, email verification (+ resend), login/logout, forgot/
  reset password, change password.
- Signed, single-use, time-limited tokens (`itsdangerous`) for email
  verification and password reset.
- Fixed a token-collision bug: two tokens issued for the same user
  within the same second were byte-for-byte identical (itsdangerous
  signs deterministically), colliding on the database's unique
  constraint — fixed with a random nonce in the signed payload.

## Phase 1 — Data layer
- All models from the spec: `User`, `Project`, `ProjectFile`,
  `Conversation`, `Message`, `CodeReview`, `CodeAnalysis`,
  `GeneratedTest`, `Document`, plus the email-verification and
  password-reset token tables.

## Phase 0 — Scaffolding
- Flask app factory, React + Vite + Tailwind shell, dev/test/prod
  config split, `.env.example` files.
