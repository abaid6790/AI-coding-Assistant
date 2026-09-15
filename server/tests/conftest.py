import pytest

from app import create_app
from extensions import db as _db


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register_and_verify(client, email="user@example.com", password="Passw0rd!"):
    """Helper: register a user then verify their email directly via the
    token service (bypassing the actual email send) so tests can log in."""
    from models.user import User
    from extensions import db

    client.post("/api/auth/register", json={"email": email, "password": password})
    user = User.query.filter_by(email=email).first()
    user.is_email_verified = True
    db.session.commit()
    return user


def login_as(client, email, password="Passw0rd!"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp
