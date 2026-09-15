# Contributing

## Local setup

See the "Running it locally" section in `README.md` for full detail,
or `docs/development/setup.md` for the scripted shortcut. Short version:

```bash
pip install -r server/requirements.txt
cp .env.example .env
python app.py
```

`python app.py` from the project root runs everything — builds the
frontend on first run, then serves the whole app (API + frontend) from
one process on `:5000`. If you're actively editing frontend code, use
the two-dev-server hot-reload workflow instead (see README) so you see
changes without rebuilding on every save.

## Project layout

- `src/` — React + Vite + Tailwind SPA, talking to the backend over
  `/api/*` (proxied in dev via `vite.config.js`). Components are
  grouped by domain (`components/common/`, `auth/`, `chat/`, `code/`,
  `analysis/`), not dumped in one flat folder.
- `server/` — Flask API. `app.py` is the entry point; `api/`
  (routes), `models/`, `services/`, `utils/` are flat top-level
  packages (no nested `app/` package). Routes stay thin — they parse
  the request, call one function in `services/`, and return its
  result; business logic lives in the service, not the route. See
  `docs/architecture/overview.md` for the full layering rule.
- `data/`, `migrations/`, `scripts/`, `docs/` — see their own
  README/overview files for what each is for.

There's no `backend/`/`frontend/` wrapper folder — `src/` and `server/`
sit side by side at the project root.

## Before opening a PR

1. **Run the backend test suite**: `cd server && python -m pytest tests/ -v`
   — all 135 tests must pass. If you add a route, add a service-level
   test too where it makes sense (see `tests/services/` for the
   pattern — calling a service function directly, no HTTP round-trip)
   plus an isolation test (see `tests/projects/test_isolation.py`:
   can User B see/modify/delete User A's resource? Should always be
   404, never 403 — see `utils/ownership.py`'s docstring for why the
   distinction matters).
2. **Build the frontend**: `npm run build` (from the project root) —
   must complete with no errors.
3. Keep provider-specific AI code inside `server/services/ai/providers/`
   — routes and services should only ever talk to `AIService`, never
   to Gemini (or any other provider) directly. See
   `services/ai/base.py` for the interface every provider implements.
4. Any new mutating endpoint should use `@login_required` and scope its
   queries through `utils/ownership.py`'s `get_owned_or_404`/
   `owned_query` — never `Model.query.get(id)` directly on a
   user-owned resource.
5. New AI-cost-bearing or abuse-prone endpoints (anything hitting an AI
   provider, sending email, or creating an account) should have a
   `@limiter.limit(...)` matching the pattern of similar existing routes.
6. Keep routes thin. If a route handler is doing more than parsing the
   request and calling a service function, the logic probably belongs
   in `services/` instead.

## Coding conventions

- Backend: standard PEP 8, type hints where they clarify intent
  (especially in `services/` and `utils/`), docstrings on anything
  non-obvious rather than restating the function name.
- Frontend: functional components with hooks, Tailwind utility classes
  (no separate CSS files per component), shared UI primitives
  (`EmptyState`, `Spinner`, `Modal`, `ScoreBar`/`FindingsList`) reused
  rather than re-implemented per screen.
- Commit messages: describe the *why* when it's not obvious from the
  diff — several bugs caught during development (a `NameError` in the
  review fallback path, an `itsdangerous` token-collision bug) were
  worth a sentence of explanation in the commit, not just "fix bug".

## Adding a new AI provider

1. Create `server/services/ai/providers/<provider>.py` implementing the
   `AIProvider` interface from `base.py` (see `gemini.py` for a full
   implementation, or `groq.py`/`openrouter.py`/`claude.py` for the
   stub pattern).
2. Add its API key(s) to `config.py` and `.env.example`.
3. Register it in `AIService._build_providers()` in `services/ai/service.py`.
4. Nothing else needs to change — routes, chat, and the code-
   intelligence features all call `AIService.generate()`.

## Reporting bugs / security issues

Regular bugs: open a GitHub issue with steps to reproduce.
Security issues: see `SECURITY.md` — please don't open a public issue
for those.
