# Changelog

All notable changes to this project, organized by build phase. See
`README.md` for full technical detail on any phase below.

## Phase 17 — Execution hardening

Closes the specific gaps Phase 12 documented as open, plus adds a
concurrency cap. All stdlib-only, zero new dependencies.

- **Whole-process-tree killing on timeout/output-cap**, not just the
  direct child (`_kill_process_tree()` in `services/execution/common.py`)
  — POSIX via `os.killpg()` on the process group `start_new_session=True`
  already created; Windows via `taskkill /F /T` (`CTRL_BREAK_EVENT`
  alone only works for processes that opt in to handling it, which
  arbitrary executed code won't). Verified with an actual test that
  spawns a real grandchild process and confirms it's dead afterward —
  not assumed from the code. That test initially "failed" in a
  confusing way: `os.kill(pid, 0)` reported the grandchild as "alive"
  after the kill. Traced it to `/proc/<pid>/status` showing state `Z`
  (zombie) — the process genuinely was dead, just unreaped, because
  this sandboxed test container has no init/subreaper (like `tini`) to
  promptly adopt and reap orphaned processes. Fixed the test's
  aliveness check to read actual process state rather than table-entry
  presence; the underlying kill mechanism had been correct all along.
- **Memory and CPU ceilings on POSIX** (`RLIMIT_AS`, `RLIMIT_CPU`),
  applied via a small self-exec bootstrap rather than `subprocess.Popen`'s
  `preexec_fn` — Python's own docs warn `preexec_fn` is unsafe in a
  multi-threaded parent process, which this Flask app genuinely is
  (and `run_subprocess()` itself spawns drain threads around the same
  `Popen` call). The bootstrap sets limits on itself as ordinary
  top-level code, then `os.execvp()`s into the real target; POSIX
  guarantees rlimits survive `exec()`, so the end result is identical
  to what `preexec_fn` would have done, without the deadlock risk.
  **Caught a real cross-language bug via the test suite, not
  documentation**: applying the same 256MB `RLIMIT_AS` ceiling to
  JavaScript broke every single Node execution — `"Fatal process out
  of memory"` before any user code even ran. Node's V8 engine reserves
  a large chunk of virtual address space upfront for its heap/CodeRange
  as normal startup behavior, unrelated to actual memory used; a
  ceiling sized for Python's much smaller footprint made V8 itself fail
  to initialize. Fixed by making the memory limit opt-in per runner
  (`apply_memory_limit` parameter, threaded through `run_subprocess()`/
  `run_in_temp_dir()`) — `python_runner.py` passes `True`,
  `node_runner.py` passes `False` and relies on the timeout, CPU
  ceiling, and output cap alone. Documented in both modules' docstrings
  so the asymmetry is explained, not silently inconsistent.
- **Concurrency cap** (`MAX_CONCURRENT_EXECUTIONS = 5`, an in-process
  `threading.Semaphore`) — bounds how many executions can run at once
  in one worker process. Acquired non-blocking; a request that can't
  get a slot raises `ExecutionCapacityError`, which
  `services/code/execution_service.py` translates into a real `503`,
  deliberately kept separate from the run-result envelope (`success:
  false`) since "the server is busy" is a request-level failure, not a
  code-execution outcome. Documented as per-process, not global across
  a multi-worker deployment — same caveat the existing rate limiter
  already has.
- 9 new tests (5 hardening-specific, 4 already-passing carried through
  unchanged): process-tree kill verified via a real spawned grandchild
  process, a real memory-bomb script hitting the RLIMIT_AS ceiling
  (skipped on platforms without `/proc`, since the verification method
  is Linux-specific even though the underlying `resource` module works
  on POSIX generally), the concurrency cap actually rejecting a second
  execution while the first holds the only slot, the slot correctly
  releasing after a run completes, and the route surfacing a clean 503.
  Stability-checked by running the timing-sensitive tests three times
  in a row before considering them done, not just once.
- `SECURITY.md` updated: the code-execution row and "Known gaps" entry
  now distinguish what Phase 17 actually closed (process-tree kill,
  POSIX memory/CPU ceilings) from what's still genuinely open (network
  isolation, filesystem access restriction, Windows memory/CPU limits,
  the concurrency cap's per-process scope) — deliberately did not
  attempt a partial/fragile version of network isolation, since that
  would create false confidence rather than real protection.

## Phase 16 — JavaScript execution

Second runnable language, on top of Phase 12's shared execution
primitives — zero new dependencies, since Node is already required for
the frontend build.

- `server/services/execution/node_runner.py`: `run_javascript()`,
  built on the exact same `run_in_temp_dir()`/`run_subprocess()` shared
  by `python_runner.py` — same scrubbed environment, temp directory,
  timeout, and output cap, just running `node main.js` instead of
  `python main.py`. Includes a clear fallback message (not a raw
  `FileNotFoundError`) if Node genuinely isn't on the server's `PATH`.
- Registered in `services/execution/__init__.py`'s `SUPPORTED_LANGUAGES`
  — `/api/code/run` now accepts `"language": "javascript"` with no
  route changes needed (the error message listing supported languages
  updates automatically too).
- Frontend: `javascript` added to `CodeEditor`'s `RUNNABLE_LANGUAGES`,
  enabling the Run button for `.js` files.
- Tests scoped to what's actually new (4 service-level: happy path,
  Node's own syntax/runtime error formats, the "Node not found"
  fallback; 3 route-level: JS through the real endpoint, a JS runtime
  error still returning 200, language-name case-insensitivity) rather
  than re-proving the shared safety mechanisms Phase 12's Python tests
  already cover — env scrubbing, temp-dir isolation, timeout
  enforcement, and output capping are the same code path regardless of
  language.
- Verified end to end against the real running app (not just pytest):
  registered a user, logged in, ran `[1,2,3].map(n => n * 2)` through
  the actual `/api/code/run` route, confirmed `[ 2, 4, 6 ]` came back.

## Phase 14-15 — Online Code Editor upgrade: Run Code UI + Fix with AI

Frontend half of the Online Code Editor & Code Runner upgrade, on top
of Phase 12-13's execution service and `/api/code/run` route.

- **Phase 14**: a clearly-visible green "▶ Run Code" button in the
  editor toolbar (disabled with an explanatory tooltip for any
  language other than Python, matching the backend's current support),
  `Ctrl/Cmd+Enter` as a run shortcut alongside the existing
  `Ctrl/Cmd+S` save shortcut, and a new `OutputPanel` showing a running
  state, then stdout/stderr/exit code with success and error visually
  distinguished (green/red), plus explicit messages for timeout and
  output-truncation outcomes rather than folding them into a generic
  failure. Runs whatever's currently in the editor, unsaved changes
  included; clears on every new run and when switching files.
- **Phase 15**: "✨ Fix with AI" wiring — appears on the output panel
  only when a run errors. Calls the *existing* `/api/code/debug`
  endpoint directly (the same one `AiActionsModal`'s Debug tab already
  used since Phase 8) with the current code and the captured stderr as
  context, then reuses the *existing* `diffProposal`/`DiffReviewModal`
  accept-flow already wired for every other AI-suggested change in the
  app. No new AI system, no new backend route, no new diff UI — purely
  connecting two things that already existed. Verified the entire
  spec-described loop end to end against the real backend (mocking
  only the AI provider call, not the execution): run buggy code → real
  `NameError` → Fix with AI → real corrected code returned → run the
  corrected code again → succeeds. Also: accepting *any* AI diff now
  clears a stale run-output panel, since the code just changed and the
  old output no longer reflects it — a small correctness fix that
  applies to every diff-review accept, not just this new flow.

## Phase 12-13 — Online Code Editor upgrade: execution service + Run Code route

First two phases of the Online Code Editor & Code Runner upgrade
(frontend Run button/Output panel and Fix with AI wiring land in
Phases 14-15).

- **Phase 12**: `server/services/execution/` — code runs in a separate
  OS process (never `exec()`/`eval()` in the Flask process), with a
  scrubbed environment (app secrets never reach the child), a fresh
  temp directory per run (cleaned up immediately after), a wall-clock
  timeout that forcibly kills the process, and an output-size cap that
  does the same. `common.py` holds the language-agnostic primitives;
  `python_runner.py` is the thin Python-specific layer on top —
  structured so a Phase 16 JavaScript runner reuses the same
  primitives instead of duplicating them. 11 tests, each targeting one
  specific safety claim (env scrubbing, temp-dir isolation, timeout
  enforcement, output capping) rather than only the happy path.
  Caught and fixed a real ordering bug during testing: closing a
  stream when the output cap trips can itself crash the child
  (`BrokenPipeError`, mid-write) before the poll loop's next tick,
  which was silently losing the `truncated` flag when `process.poll()`
  was checked before `stop_event.is_set()` — fixed by checking
  `stop_event` first. Also stripped the server's temp-directory path
  out of tracebacks so output matches the spec's clean `File "main.py"`
  example instead of leaking a server-side filesystem path.
- **Phase 13**: `POST /api/code/run` (`services/code/execution_service.py`
  + a route in `api/code.py`, following the exact pattern every other
  code-intelligence route already uses). A failed run (syntax error,
  runtime exception, timeout) is a 200 with `success: false` in the
  body — the request succeeded, the code didn't — while a genuinely
  invalid request (missing code, unsupported language) is a real 400.
  Rate-limited more generously than the AI endpoints (20/minute vs.
  30-60/hour) since running code is meant to be iterated on quickly
  and costs no external API fees, only bounded local CPU/time already
  capped per-run by Phase 12. 10 route-level tests, run against real
  Python execution (no mocking needed — it's fast and already proven
  safe by Phase 12) except for the timeout-flag plumbing test, which
  mocks the result to avoid a real 10-second wait per test run.
- `SECURITY.md` updated: the "AI response handling" row no longer
  claims code is never executed (it now is, deliberately, as this
  upgrade's whole purpose); a new row documents the execution safety
  model, and a new "Known gaps" entry is explicit that this is process
  isolation, not container/VM sandboxing.

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
