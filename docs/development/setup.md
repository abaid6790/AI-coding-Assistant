# Development setup

For coding conventions, the PR checklist, and how to add a new AI
provider, see `CONTRIBUTING.md` at the project root — this page is just
the "get it running" steps, including the scripted shortcuts that
supplement (not replace) the manual steps in the root `README.md`.

## Fastest path

```bash
python scripts/setup.py                   # creates .env from .env.example, data/ dirs
pip install -r server/requirements.txt
python app.py
```

`python app.py` (from the project root) is the single command that
runs everything — it builds the frontend automatically on first run,
then serves both the API and the built app from one process on
`:5000`. See the root `README.md`'s "Running it locally" for the
hot-reload alternative (two separate dev servers) if you're actively
editing frontend code and want to see changes without rebuilding.

Optionally seed a demo account so you're not stuck registering and
digging a verification link out of the console log:

```bash
python scripts/seed.py
# demo@example.com / DemoPass123!
```

## Running the tests

```bash
cd server
python -m pytest tests/ -v
```

Should show `135 passed` (132 covering behavior + 3 direct service-layer
unit tests — see `server/tests/services/`).

## Resetting your local environment

```bash
python scripts/cleanup.py             # clears caches + build output
python scripts/cleanup.py --db        # + drops the local SQLite database
python scripts/cleanup.py --node-modules  # + removes node_modules/
```

## Common gotchas

- **AI features return "temporarily unavailable"**: you need
  `GEMINI_API_KEY_1` set in `.env`. Everything else (auth, projects,
  files, the editor) works without it.
- **Emails don't arrive**: `MAIL_SUPPRESS_SEND=true` by default —
  verification/reset links are logged to the backend console instead.
  Set it to `false` with real `MAIL_*` credentials to send real email.
- **CSRF 403 on a request you're making manually (curl, Postman)**:
  expected — see `SECURITY.md`. The frontend handles this
  automatically; a manual request needs to read the `csrf_token` cookie
  and echo it in an `X-CSRF-Token` header.
