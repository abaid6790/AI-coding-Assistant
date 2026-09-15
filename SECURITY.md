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
| AI response handling | User-submitted code is never executed; AI-generated code changes require explicit user review/accept via a diff view before being applied |

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

If you're taking this to production, treat the above as your starting
checklist, not a to-do list to skip.
