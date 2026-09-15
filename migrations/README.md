# Migrations

This project currently uses SQLAlchemy's `db.create_all()` (called once
at app startup in `server/app.py`) rather than versioned migrations —
appropriate for the SQLite-by-default, single-developer setup this was
built for, but worth being explicit about rather than pretending
otherwise with empty placeholder migration files.

## What this means in practice

- On a fresh database, all tables are created automatically from the
  current model definitions (`server/models/`) the first time the app
  starts.
- **Schema changes to an existing database are not automated.** If you
  add a column to a model, you either need to recreate the database
  (fine in development — see `scripts/cleanup.py --db`) or apply the
  schema change manually.

## Adding real migrations (Alembic / Flask-Migrate)

This directory is reserved for when the project needs them — likely
once there's a shared database that can't just be dropped and recreated
(a staging/production environment, or multiple developers with data
they want to keep). At that point:

```bash
pip install Flask-Migrate
```

then in `server/extensions.py`, add a `Migrate` instance and initialize
it in `server/app.py`'s `_init_extensions()` alongside the other
extensions, and replace the `db.create_all()` call with
`flask db upgrade` as part of your deploy step. Flask-Migrate will
generate versioned migration scripts into this directory from that
point on.

This wasn't added as part of the restructure that created this
directory — doing so would be a real behavior change (a new dependency,
a new startup step), not a folder reorganization, and the restructure
this file accompanies was explicitly scoped to preserve existing
behavior exactly.
