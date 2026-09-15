"""
Signed, time-limited tokens for email verification and password reset.

We use itsdangerous URLSafeTimedSerializer so the token itself carries a
tamper-proof signature — no need to keep a secret list in memory. We still
persist a row per issued token (EmailVerificationToken / PasswordResetToken)
so a token can be marked used and can't be replayed.
"""
import uuid

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

from extensions import db
from models.tokens import EmailVerificationToken, PasswordResetToken

_EMAIL_SALT = "email-verification"
_RESET_SALT = "password-reset"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _dumps(user_id: str, salt: str) -> str:
    # itsdangerous signs (payload + timestamp) deterministically, so two
    # tokens issued for the same user within the same second would
    # otherwise be byte-for-byte identical and collide on the token
    # table's unique constraint. A random nonce in the payload guarantees
    # uniqueness regardless of timing.
    payload = f"{user_id}:{uuid.uuid4().hex}"
    return _serializer().dumps(payload, salt=salt)


def _loads(token: str, salt: str, max_age: int) -> str:
    payload = _serializer().loads(token, salt=salt, max_age=max_age)
    user_id, _, _nonce = payload.partition(":")
    return user_id


def issue_email_verification_token(user_id: str) -> str:
    token = _dumps(user_id, _EMAIL_SALT)
    record = EmailVerificationToken(user_id=user_id, token=token)
    db.session.add(record)
    db.session.commit()
    return token


def issue_password_reset_token(user_id: str) -> str:
    token = _dumps(user_id, _RESET_SALT)
    record = PasswordResetToken(user_id=user_id, token=token)
    db.session.add(record)
    db.session.commit()
    return token


class TokenError(Exception):
    """Raised for any invalid/expired/already-used token — callers should
    show a generic 'invalid or expired link' message, never the specific
    reason, to avoid leaking whether an email exists."""


def _consume(token: str, salt: str, max_age: int, model):
    try:
        user_id = _loads(token, salt=salt, max_age=max_age)
    except SignatureExpired:
        raise TokenError("expired")
    except BadSignature:
        raise TokenError("invalid")

    record = model.query.filter_by(token=token, user_id=user_id).first()
    if record is None:
        raise TokenError("unknown")
    if record.is_used:
        raise TokenError("already_used")

    from datetime import datetime, timezone
    record.used_at = datetime.now(timezone.utc)
    db.session.commit()
    return user_id


def consume_email_verification_token(token: str) -> str:
    max_age = current_app.config["EMAIL_VERIFICATION_TOKEN_MAX_AGE"]
    return _consume(token, _EMAIL_SALT, max_age, EmailVerificationToken)


def consume_password_reset_token(token: str) -> str:
    max_age = current_app.config["PASSWORD_RESET_TOKEN_MAX_AGE"]
    return _consume(token, _RESET_SALT, max_age, PasswordResetToken)
