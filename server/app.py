"""
The Flask application: API routes under /api/*, plus the built React
frontend (dist/) served for every other route, so one process on one
port runs the whole application.

Recommended way to run the whole app with a single command:

    python app.py         # from the PROJECT ROOT (not this directory)

That root-level app.py builds the frontend automatically if it hasn't
been built yet, then runs this module. Running this file directly
(`python app.py` from inside server/) also works and is useful for
backend-only development, but expects the frontend to already be built
(`npm run build` from the project root) if you want / to serve
anything other than a "not built yet" message.

Everything else (models, routes, services, utils) lives in flat
top-level packages next to this file — models/, api/, services/,
utils/ — imported as e.g. `from models.user import User`, not nested
under an `app/` package. That's a deliberate structure choice: one
fewer level of indirection between "what file has this code" and "what
do I type to import it".
"""
import os

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, send_from_directory, abort  # noqa: E402

from config import config_by_name  # noqa: E402
from extensions import db, login_manager, mail, cors, limiter  # noqa: E402

# The built frontend (npm run build) lands in <project_root>/dist —
# one level up from this file's directory (server/). Serving it from
# this same Flask process means one process, one port, one command
# (`python app.py` at the project root) runs the whole application —
# no separate frontend dev server required.
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist")
FRONTEND_DIST = os.path.normpath(FRONTEND_DIST)


def create_app(env: str | None = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[env])

    # SQLite (dev/test default) and the reserved uploads/projects dirs
    # all live under the project-level data/ directory — see config.py.
    # TestingConfig uses an in-memory DB, so this is a harmless no-op
    # in tests (the dirs just aren't used).
    for path in (app.config.get("UPLOADS_DIR"), app.config.get("PROJECTS_DIR")):
        if path:
            os.makedirs(path, exist_ok=True)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
        db_path = app.config["SQLALCHEMY_DATABASE_URI"].removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_csrf_protection(app)
    _register_frontend(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}},
        supports_credentials=True,
    )

    login_manager.init_app(app)
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id: str):
        from models.user import User
        return db.session.get(User, user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required."}), 401

    # Import models so they're registered on db.metadata before create_all.
    import models  # noqa: F401

    with app.app_context():
        db.create_all()


def _register_csrf_protection(app: Flask) -> None:
    """Double-submit-cookie CSRF check (see utils/csrf.py) for
    authenticated, state-changing requests. Endpoints reachable before a
    session exists are exempt — see the module docstring in utils/csrf.py
    for why."""
    from flask import request, abort
    from flask_login import current_user
    from utils.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, tokens_match

    exempt_paths = {
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/forgot-password",
        "/api/auth/reset-password",
        "/api/auth/verify-email",
        "/api/auth/resend-verification",
        "/api/health",
    }

    @app.before_request
    def enforce_csrf():
        if not app.config.get("WTF_CSRF_ENABLED", True):
            return  # disabled in TestingConfig
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return
        if not request.path.startswith("/api/") or request.path in exempt_paths:
            return
        if not current_user.is_authenticated:
            return  # nothing to protect: no session to ride yet

        cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
        header_value = request.headers.get(CSRF_HEADER_NAME)
        if not tokens_match(cookie_value, header_value):
            abort(403)  # handled by the generic 403 error handler below


def _register_frontend(app: Flask) -> None:
    """Serves the built React app (dist/) for every route that isn't
    /api/*. This is what makes `python app.py` a single command that
    runs the whole application — the frontend is static files served
    by this same process, not a separate dev server on another port.

    If dist/ doesn't exist (frontend never built), this degrades to a
    clear message instead of a confusing generic 404 — see app.py at
    the project root, which builds the frontend automatically before
    ever reaching this point in the normal `python app.py` flow.
    """
    has_build = os.path.isfile(os.path.join(FRONTEND_DIST, "index.html"))

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        if path.startswith("api/"):
            abort(404)  # never let the SPA catch-all swallow an API 404

        if not has_build:
            return (
                "Frontend not built yet. Run `python app.py` from the "
                "project root (not server/) — it builds the frontend "
                "automatically on first run. Or build it manually: "
                "`npm install && npm run build` from the project root.",
                503,
            )

        requested = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(requested):
            return send_from_directory(FRONTEND_DIST, path)
        # Any other path (e.g. /dashboard, /projects/<id>) is a client-side
        # route — let React Router handle it by serving the SPA shell.
        return send_from_directory(FRONTEND_DIST, "index.html")


def _register_blueprints(app: Flask) -> None:
    from api.auth import auth_bp
    from api.projects import projects_bp
    from api.conversations import conversations_bp
    from api.ai import ai_bp
    from api.code import code_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(code_bp)

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok"})


def _register_error_handlers(app: Flask) -> None:
    """Never leak stack traces or internal exception text to the client —
    log the real error server-side, return a generic message to the user."""

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return jsonify({"error": "Forbidden."}), 403

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify({"error": "File too large."}), 413

    @app.errorhandler(429)
    def rate_limited(_e):
        return jsonify({"error": "Too many requests. Please slow down."}), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.error("Unhandled exception", exc_info=e)
        return jsonify({"error": "Something went wrong. Please try again."}), 500


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\nAI Coding Assistant running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
