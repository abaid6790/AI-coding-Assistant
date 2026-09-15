import re
from flask import jsonify

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LENGTH = 8


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(_EMAIL_RE.match(email.strip()))


def password_errors(password: str) -> list[str]:
    """Returns a list of human-readable problems; empty list = valid."""
    errors = []
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password and not re.search(r"[A-Za-z]", password):
        errors.append("Password must contain at least one letter.")
    if password and not re.search(r"[0-9]", password):
        errors.append("Password must contain at least one number.")
    return errors


def error_response(message: str, status: int = 400, field_errors: dict | None = None):
    """Uniform error shape. Never include internal exception text here —
    that belongs in server logs only (see app.py error handlers)."""
    payload = {"error": message}
    if field_errors:
        payload["field_errors"] = field_errors
    return jsonify(payload), status


# ---------------------------------------------------------------------------
# File / path safety (spec: "Validate file types and sizes", "File
# validation" under security). folder_path/filename are plain string
# columns, not real filesystem paths — nothing here touches disk — but
# the app's own file-tree logic (frontend) and any future export/zip
# feature would misbehave on ".." segments or null bytes, so we reject
# them at the API boundary rather than trusting every caller downstream
# to handle them safely.
# ---------------------------------------------------------------------------

# Filenames with no extension are only allowed if they're on this list —
# common, unambiguous conventions, not an open door for arbitrary
# extensionless files.
ALLOWED_FILENAMES_WITHOUT_EXTENSION = {
    "dockerfile", "makefile", "readme", "license", "procfile",
    "gemfile", "rakefile", ".gitignore", ".env.example", ".dockerignore",
}


def is_valid_filename(filename: str) -> bool:
    """Structural safety only — no path separators, no traversal, no
    null bytes, no leading/trailing whitespace, reasonable length. Does
    NOT check the extension allowlist; see validate_file_extension for that."""
    if not filename or len(filename) > 255:
        return False
    if filename != filename.strip():
        return False
    if "\x00" in filename:
        return False
    if "/" in filename or "\\" in filename:
        return False
    if filename in (".", ".."):
        return False
    return True


def is_valid_folder_path(folder_path: str) -> bool:
    """Empty string (root) is valid. Otherwise: forward-slash separated
    segments, none of which may be '.', '..', or empty (no leading/
    trailing/double slashes), no null bytes."""
    if folder_path == "":
        return True
    if "\x00" in folder_path:
        return False
    if folder_path != folder_path.strip():
        return False
    segments = folder_path.split("/")
    return all(seg and seg not in (".", "..") for seg in segments)


def validate_file_extension(filename: str, allowed_extensions: set[str]) -> bool:
    """filename is assumed already structurally valid (is_valid_filename).
    A file with no extension is allowed only if it's a recognized
    convention (Dockerfile, Makefile, ...); everything else must match
    the configured allowlist, case-insensitively."""
    name = filename.rsplit("/", 1)[-1]
    if "." not in name:
        return name.lower() in ALLOWED_FILENAMES_WITHOUT_EXTENSION
    ext = name.rsplit(".", 1)[-1].lower()
    return ext in allowed_extensions
