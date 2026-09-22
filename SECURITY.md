# Security Policy

## Reporting a vulnerability

If you find a security issue in this project, please report it privately
rather than opening a public GitHub issue.

- Email: [security@your-domain.example] (replace with a real address before publishing this repo)
- Please include: a description of the issue, steps to reproduce, and
  the potential impact.
- We'll acknowledge reports within a few days and aim to have a fix or
  mitigation plan within two weeks for confirmed issues.

Please don't publicly disclose a vulnerability until it's been addressed.

## Supported versions

This project doesn't yet have tagged releases. Security fixes are
applied to the `main` branch only.

## What's already covered

This isn't a claim of "secure" in any absolute sense — it's a list of
what's been deliberately built and tested, so a reviewer knows what to
check first and what's still open.

| Area | What's in place |
|---|---|
| Authentication | Email/password with Werkzeug PBKDF2 hashing, email verification required before login, forgot/reset password via signed single-use time-limited tokens (`itsdangerous`) |
| Session management | Flask-Login with `session_protection="strong"`, HttpOnly + SameSite=Lax cookies, `Secure` flag enforced in production config |
| CSRF | Double-submit cookie (`server/utils/csrf.py`) — every authenticated mutating request requires an `X-CSRF-Token` header matching a cookie set at login, checked in constant time |
| Multi-user isolation | Every resource query is scoped to the authenticated user via `server/utils/ownership.py`; the authenticated user id is always derived from the session, never a client-supplied field; 20+ dedicated isolation tests |
| Rate limiting | Flask-Limiter on account creation, login, password reset, email verification, and every AI-cost-bearing endpoint |
| File validation | Filename/folder-path structural checks (no path traversal, null bytes, path separators) and an extension allowlist, enforced at the API boundary |
| Error handling | Generic error responses to clients; real exceptions logged server-side only, never returned with stack traces |
| Secrets | All credentials (`SECRET_KEY`, mail credentials, Gemini API keys) come from environment variables, never hardcoded; `.env` is gitignored |
| AI response handling | AI-generated code changes require explicit user review/accept via a diff view before being applied — never auto-applied |
| Code execution (Run Code feature) | User-submitted code runs in a separate OS process (never `exec()`/`eval()` inside the Flask process) with a scrubbed environment (no app secrets reachable — `SECRET_KEY`, API keys, DB credentials are never passed through), a fresh temp directory per run, a 10s wall-clock timeout, an output-size cap, and (Phase 17) a concurrency cap so one user can't exhaust the server with simultaneous runs. On timeout or the output cap, the **entire process tree is killed** (not just the direct child — closed a gap Phase 12 had explicitly documented as open), verified by an actual test that spawns a grandchild process and confirms it's dead afterward, not just assumed. On POSIX, a memory ceiling and CPU-time ceiling are also enforced as a backstop (deliberately **not** applied to JavaScript — Node's V8 engine reserves large virtual address space upfront that a small memory ceiling would break; discovered by this phase's own tests failing, not assumed safe). See `server/services/execution/common.py`'s docstring for exactly what this does and does not cover — it's process isolation, not container/VM sandboxing (see Known gaps below) |

## Known gaps (not yet done)

Being upfront about these matters more than padding the list above:

- **No professional penetration test or third-party audit.**
- **No automated dependency vulnerability scanning** (`pip-audit`,
  `npm audit`, Dependabot, or similar) wired into CI — there's no CI yet
  either.
- **Rate limiting uses in-memory storage** (Flask-Limiter default) —
  fine for a single process, not safe against bypass in a multi-worker/
  multi-instance production deployment. Use a shared backend (Redis) in
  production.
- **No Content Security Policy (CSP) header** is set on frontend
  responses.
- **No automated secret-scanning** on commits (e.g. gitleaks) is
  configured.
- The three stub AI providers (Groq, OpenRouter, Claude) are
  architecture only — verify their real implementations against this
  same checklist before enabling them.
- **Code execution (Run Code feature) is process isolation, not a
  container/VM sandbox.** As of Phase 17: memory/CPU ceilings (POSIX
  only — Python only, not JavaScript, see the table above) and
  whole-process-tree killing on timeout are both in place now. What's
  still genuinely missing: **no network isolation** (executed code can
  make outbound network requests — deliberately not attempted with a
  partial in-process measure, since that would create false confidence
  rather than real protection; this needs an actual container/VM),
  **no filesystem access restriction** beyond running in an empty temp
  directory (the code can still read any path the server process has
  OS permission to read), **no memory/CPU ceiling on Windows** (no
  stdlib equivalent to POSIX's `resource` module without adding a
  dependency), and **the concurrency cap is per-process**, not global
  across a multi-worker deployment — same caveat the rate limiter
  already has. This is explicitly a development-stage mechanism (see
  `server/services/execution/common.py`'s docstring); do not expose it
  to untrusted users in production without adding real sandboxing (a
  container per run, gVisor, Firecracker, or similar) first.

If you're taking this to production, treat the above as your starting
checklist, not a to-do list to skip.
