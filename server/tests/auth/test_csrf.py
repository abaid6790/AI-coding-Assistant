"""
The shared `client` fixture (conftest.py) uses TestingConfig, which has
WTF_CSRF_ENABLED = False so the other 104+ tests don't need to carry a
CSRF cookie/header on every mutating request. These tests build their
own app instance with CSRF turned back on, specifically to verify the
protection itself works — everything here is self-contained and doesn't
touch the shared fixture.
"""
import pytest

from app import create_app
from extensions import db as _db
from utils.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, tokens_match, generate_csrf_token


@pytest.fixture
def csrf_app():
    application = create_app("testing")
    application.config["WTF_CSRF_ENABLED"] = True
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def csrf_client(csrf_app):
    return csrf_app.test_client()


def _register_verify_login(client, email="csrf@example.com", password="Passw0rd!"):
    from models.user import User

    client.post("/api/auth/register", json={"email": email, "password": password})
    user = User.query.filter_by(email=email).first()
    user.is_email_verified = True
    _db.session.commit()
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Unit tests for the comparison itself
# ---------------------------------------------------------------------------
def test_tokens_match_requires_both_present():
    assert tokens_match(None, None) is False
    assert tokens_match("abc", None) is False
    assert tokens_match(None, "abc") is False


def test_tokens_match_requires_equal_values():
    assert tokens_match("abc", "xyz") is False
    assert tokens_match("abc", "abc") is True


def test_generate_csrf_token_is_random_and_reasonably_long():
    a, b = generate_csrf_token(), generate_csrf_token()
    assert a != b
    assert len(a) >= 32


# ---------------------------------------------------------------------------
# End-to-end: login sets the cookie, mutating requests need the header
# ---------------------------------------------------------------------------
def test_login_sets_csrf_cookie(csrf_client):
    resp = _register_verify_login(csrf_client)
    assert resp.status_code == 200
    set_cookie_headers = resp.headers.getlist("Set-Cookie")
    assert any(CSRF_COOKIE_NAME in h for h in set_cookie_headers)


def test_mutating_request_without_csrf_header_is_rejected(csrf_client):
    _register_verify_login(csrf_client)
    # The test client automatically carries cookies from the login
    # response (including the CSRF cookie) but we deliberately don't
    # attach the header — simulating a cross-site forged request, which
    # can trigger the cookie-bearing request but can't read the cookie
    # to build a matching header.
    resp = csrf_client.post("/api/projects", json={"name": "should be blocked"})
    assert resp.status_code == 403


def test_mutating_request_with_correct_csrf_header_succeeds(csrf_client):
    login_resp = _register_verify_login(csrf_client)
    cookie_value = None
    for h in login_resp.headers.getlist("Set-Cookie"):
        if h.startswith(f"{CSRF_COOKIE_NAME}="):
            cookie_value = h.split(";")[0].split("=", 1)[1]

    assert cookie_value, "CSRF cookie should have been set on login"

    resp = csrf_client.post(
        "/api/projects",
        json={"name": "allowed"},
        headers={CSRF_HEADER_NAME: cookie_value},
    )
    assert resp.status_code == 201


def test_mutating_request_with_wrong_csrf_header_is_rejected(csrf_client):
    _register_verify_login(csrf_client)
    resp = csrf_client.post(
        "/api/projects",
        json={"name": "should be blocked"},
        headers={CSRF_HEADER_NAME: "totally-wrong-value"},
    )
    assert resp.status_code == 403


def test_get_requests_do_not_require_csrf_header(csrf_client):
    _register_verify_login(csrf_client)
    resp = csrf_client.get("/api/projects")
    assert resp.status_code == 200


def test_login_itself_is_exempt_from_csrf_check(csrf_client):
    # No CSRF cookie exists yet before login — the endpoint that
    # establishes the session can't require a token tied to that session.
    resp = _register_verify_login(csrf_client)
    assert resp.status_code == 200


def test_logout_clears_csrf_cookie(csrf_client):
    login_resp = _register_verify_login(csrf_client)
    cookie_value = None
    for h in login_resp.headers.getlist("Set-Cookie"):
        if h.startswith(f"{CSRF_COOKIE_NAME}="):
            cookie_value = h.split(";")[0].split("=", 1)[1]

    logout_resp = csrf_client.post("/api/auth/logout", headers={CSRF_HEADER_NAME: cookie_value})
    assert logout_resp.status_code == 200
    assert any(
        h.startswith(f"{CSRF_COOKIE_NAME}=") and ("Max-Age=0" in h or "expires=Thu, 01-Jan-1970" in h)
        for h in logout_resp.headers.getlist("Set-Cookie")
    )
