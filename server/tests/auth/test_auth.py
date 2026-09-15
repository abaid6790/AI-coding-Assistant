from tests.conftest import register_and_verify


def test_register_creates_unverified_user(client):
    resp = client.post("/api/auth/register", json={
        "email": "new@example.com", "password": "Passw0rd!",
    })
    assert resp.status_code == 201
    assert resp.get_json()["user"]["is_email_verified"] is False


def test_register_rejects_weak_password(client):
    resp = client.post("/api/auth/register", json={
        "email": "weak@example.com", "password": "abc",
    })
    assert resp.status_code == 400


def test_register_rejects_invalid_email(client):
    resp = client.post("/api/auth/register", json={
        "email": "not-an-email", "password": "Passw0rd!",
    })
    assert resp.status_code == 400


def test_register_rejects_duplicate_email(client):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "Passw0rd!"})
    resp = client.post("/api/auth/register", json={"email": "dup@example.com", "password": "Passw0rd!"})
    assert resp.status_code == 409


def test_login_blocked_before_email_verification(client):
    client.post("/api/auth/register", json={"email": "unverified@example.com", "password": "Passw0rd!"})
    resp = client.post("/api/auth/login", json={"email": "unverified@example.com", "password": "Passw0rd!"})
    assert resp.status_code == 403


def test_login_wrong_password_is_401_not_404(client):
    register_and_verify(client, email="realuser@example.com")
    resp = client.post("/api/auth/login", json={"email": "realuser@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email_is_401_not_404(client):
    resp = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever1"})
    assert resp.status_code == 401


def test_full_login_logout_flow(client):
    register_and_verify(client, email="flow@example.com")

    login_resp = client.post("/api/auth/login", json={"email": "flow@example.com", "password": "Passw0rd!"})
    assert login_resp.status_code == 200

    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.get_json()["user"]["email"] == "flow@example.com"

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200

    me_after_logout = client.get("/api/auth/me")
    assert me_after_logout.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_change_password_requires_correct_current_password(client):
    register_and_verify(client, email="cp@example.com")
    client.post("/api/auth/login", json={"email": "cp@example.com", "password": "Passw0rd!"})

    resp = client.post("/api/auth/change-password", json={
        "current_password": "wrong", "new_password": "NewPassw0rd!",
    })
    assert resp.status_code == 401


def test_change_password_success_then_relogin(client):
    register_and_verify(client, email="cp2@example.com")
    client.post("/api/auth/login", json={"email": "cp2@example.com", "password": "Passw0rd!"})

    resp = client.post("/api/auth/change-password", json={
        "current_password": "Passw0rd!", "new_password": "NewPassw0rd!",
    })
    assert resp.status_code == 200

    client.post("/api/auth/logout")
    relogin = client.post("/api/auth/login", json={"email": "cp2@example.com", "password": "NewPassw0rd!"})
    assert relogin.status_code == 200


def test_forgot_password_always_returns_generic_message(client):
    resp_known = client.post("/api/auth/forgot-password", json={"email": "ghost2@example.com"})
    assert resp_known.status_code == 200
    assert "If an account exists" in resp_known.get_json()["message"]


def test_reset_password_with_invalid_token_fails(client):
    resp = client.post("/api/auth/reset-password", json={"token": "garbage", "password": "NewPassw0rd!"})
    assert resp.status_code == 400


def test_verify_email_with_valid_token(client):
    from models.user import User
    from services.auth.token_service import issue_email_verification_token

    client.post("/api/auth/register", json={"email": "verifyme@example.com", "password": "Passw0rd!"})
    user = User.query.filter_by(email="verifyme@example.com").first()
    token = issue_email_verification_token(user.id)

    resp = client.post("/api/auth/verify-email", json={"token": token})
    assert resp.status_code == 200

    user_refetched = User.query.filter_by(email="verifyme@example.com").first()
    assert user_refetched.is_email_verified is True


def test_verify_email_token_cannot_be_reused(client):
    from models.user import User
    from services.auth.token_service import issue_email_verification_token

    client.post("/api/auth/register", json={"email": "onceonly@example.com", "password": "Passw0rd!"})
    user = User.query.filter_by(email="onceonly@example.com").first()
    token = issue_email_verification_token(user.id)

    first = client.post("/api/auth/verify-email", json={"token": token})
    second = client.post("/api/auth/verify-email", json={"token": token})
    assert first.status_code == 200
    assert second.status_code == 400


def test_health_check(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_tampered_session_cookie_is_treated_as_unauthenticated(client):
    """A forged/corrupted session cookie must degrade to 'not logged in'
    (Flask's signed-cookie verification rejects it) rather than crashing
    the request or, worse, being accepted as some other user's session."""
    client.set_cookie("session", "not-a-real-signed-session-value")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
