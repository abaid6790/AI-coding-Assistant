import os
from datetime import timedelta

# server/config.py -> project root is one level up from this file's directory.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATABASE_DIR = os.path.join(DATA_DIR, "database")


class Config:
    """Base config. Never hardcode secrets here — everything comes from env."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # --- Database -----------------------------------------------------
    # SQLite under the project-level data/ directory for local dev; swap
    # SQLALCHEMY_DATABASE_URI for a postgres:// URL in production. No
    # other code needs to change (SQLAlchemy abstracts it).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(DATABASE_DIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Data directories -------------------------------------------------
    # Reserved for future features (raw file uploads, exported project
    # archives) — not used by any current endpoint, but the paths are
    # defined centrally now so a future feature doesn't invent its own
    # convention. app.py ensures these exist at startup.
    UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
    PROJECTS_DIR = os.path.join(DATA_DIR, "projects")

    # --- Sessions / cookies --------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    # CSRF protection (see utils/csrf.py) is on by default; TestingConfig
    # below turns it off so the test client doesn't need to carry a
    # csrf cookie/header on every mutating request.
    WTF_CSRF_ENABLED = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # --- CORS ------------------------------------------------------------
    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

    # --- Mail (Flask-Mail) ----------------------------------------------
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@example.com")
    # When true, emails are printed to the console instead of sent —
    # convenient for local dev without SMTP credentials.
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "true").lower() == "true"

    # --- Tokens ------------------------------------------------------------
    EMAIL_VERIFICATION_TOKEN_MAX_AGE = 60 * 60 * 24  # 24 hours
    PASSWORD_RESET_TOKEN_MAX_AGE = 60 * 60  # 1 hour

    # --- Gemini / AI providers (wired up in Phase 6) --------------------
    GEMINI_API_KEYS = [
        k for k in [
            os.environ.get("GEMINI_API_KEY_1"),
            os.environ.get("GEMINI_API_KEY_2"),
            os.environ.get("GEMINI_API_KEY_3"),
            os.environ.get("GEMINI_API_KEY_4"),
        ] if k
    ]
    # Stub providers (see services/ai/{groq,openrouter,claude}.py) —
    # not implemented yet, but wiring the config through now means
    # implementing one later is just filling in _call(), no config
    # plumbing to add.
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

    # --- File uploads --------------------------------------------------
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB per request
    ALLOWED_FILE_EXTENSIONS = {
        "py", "js", "ts", "tsx", "jsx", "java", "cpp", "c", "cs", "php",
        "html", "css", "sql", "json", "md", "txt", "go", "rb", "rs",
    }


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
