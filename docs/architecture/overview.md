# Architecture overview

This is a deliberately short document — full technical detail on any
feature lives in the root `README.md` (organized phase-by-phase) and
`PRD.md` (the "what and why"). This page is the map, not the territory.

## The shape of the system

```
Browser (React SPA, src/)
    │  fetch, credentials: include, X-CSRF-Token header
    ▼
Flask API (server/), CORS-restricted to one origin
    │
    ├── api/           routes — thin, 5-15 lines each: parse request,
    │                  call a service, return its result
    ├── services/       business logic, the actual behavior
    │   ├── auth/       tokens, email sending
    │   ├── ai/         provider-agnostic AI layer (see below)
    │   ├── chat/       controlled context selection for AI chat
    │   ├── code/       the seven code-intelligence features
    │   └── projects/   project/file/folder CRUD, the analysis dashboard
    ├── models/         SQLAlchemy models — the source of truth for the schema
    └── utils/          ownership enforcement, CSRF, validation — cross-
                         cutting concerns every route/service can reach for
    │
    ▼
SQLite (data/database/app.db) — swappable for Postgres via DATABASE_URL,
no code changes required (SQLAlchemy abstracts the difference)
```

## Layering rule

Routes never contain business logic — they parse the request, call
exactly one service function, and return what it gives back. This
means every service function is independently unit-testable without
going through an HTTP request at all (see `server/tests/services/` for
examples that do exactly that), and it means the same logic could be
reused from a CLI, a background job, or another route without
duplicating it.

## The two things every route and service must respect

1. **Ownership** (`server/utils/ownership.py`): the authenticated
   user's identity always comes from the session, never a client-
   supplied field. A resource that exists but belongs to someone else
   returns the same 404 as a resource that doesn't exist — never a 403,
   which would itself leak that the ID was valid.
2. **CSRF** (`server/utils/csrf.py`): every authenticated, state-
   changing request must carry an `X-CSRF-Token` header matching a
   cookie set at login. See `SECURITY.md` for the full threat model.

## The AI provider layer

```
AIService (services/ai/service.py)
   │  — the ONLY thing routes/services should import from here
   │
   ├── GeminiProvider    (services/ai/providers/gemini.py) — implemented,
   │                      with multi-key rotation on rate limit/quota/
   │                      invalid-key/transient errors
   ├── GroqProvider       (providers/groq.py)       — stub
   ├── OpenRouterProvider (providers/openrouter.py) — stub
   └── ClaudeProvider     (providers/claude.py)     — stub
```

Adding a real provider: implement `_call()` in the matching stub
following `gemini.py`'s pattern, add its API key to `config.py`/
`.env.example`, register it in `AIService._build_providers()`. Nothing
in routes, chat, or the code-intelligence features changes — they all
call `AIService.generate()`, never a provider directly.

## Where things live, at a glance

| Concern | Location |
|---|---|
| Frontend source | `src/` (project root, no `frontend/` wrapper) |
| Backend source | `server/` (no `backend/` wrapper) |
| Runtime data (SQLite DB, reserved upload/export dirs) | `data/` |
| Utility scripts (setup, seed, cleanup) | `scripts/` |
| This documentation | `docs/` |

See the root `README.md`'s "Project structure" section for the full
file tree.
