"""
CSRF protection via the double-submit cookie pattern.

Why this instead of Flask-WTF: Flask-WTF's CSRFProtect is built around
HTML forms; this is a JSON API consumed by a React SPA over fetch, where
the natural fit is a token in a readable cookie that the frontend must
echo back in a custom header. A cross-site attacker's page can trigger
a request that automatically carries the victim's cookies, but it
cannot READ those cookies (browsers enforce same-origin on cookie
access) — so it cannot construct a matching header value. No server-side
token storage needed: validity is just "does the header match the
cookie", checked in constant time so a timing side-channel can't be used
to guess it byte-by-byte.

Scope: only authenticated, state-changing (POST/PUT/PATCH/DELETE)
requests are checked — see the exempt-path list and the
current_user.is_authenticated check in app.py's before_request hook.
Endpoints reachable before any session exists (register, login, forgot/
reset password, email verification) are exempt: there's no authenticated
session yet for a forged request to ride.
"""
import hmac
import secrets

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def tokens_match(cookie_value: str | None, header_value: str | None) -> bool:
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)
