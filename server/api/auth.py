from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from extensions import db, limiter
from models.user import User
from services.auth.token_service import (
    issue_email_verification_token,
    issue_password_reset_token,
    consume_email_verification_token,
    consume_password_reset_token,
    TokenError,
)
from services.auth.email_service import send_verification_email, send_password_reset_email
from utils.validation import is_valid_email, password_errors, error_response
from utils.csrf import CSRF_COOKIE_NAME, generate_csrf_token

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    display_name = (data.get("display_name") or "").strip() or None

    if not is_valid_email(email):
        return error_response("Please provide a valid email address.", field_errors={"email": "invalid"})

    pw_errors = password_errors(password)
    if pw_errors:
        return error_response("Password does not meet requirements.", field_errors={"password": pw_errors})

    if User.query.filter_by(email=email).first() is not None:
        # Deliberately vague to avoid confirming which emails are registered
        # in a way that's exploitable, while still being useful to the user.
        return error_response("An account with this email may already exist.", status=409)

    user = User(email=email, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = issue_email_verification_token(user.id)
    send_verification_email(user, token)

    return jsonify({
        "message": "Account created. Check your email to verify your address.",
        "user": user.to_public_dict(),
    }), 201


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
@auth_bp.route("/verify-email", methods=["POST"])
@limiter.limit("20 per hour")
def verify_email():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""

    try:
        user_id = consume_email_verification_token(token)
    except TokenError:
        return error_response("This verification link is invalid or has expired.", status=400)

    user = db.session.get(User, user_id)
    if user is None:
        return error_response("This verification link is invalid or has expired.", status=400)

    user.is_email_verified = True
    db.session.commit()
    return jsonify({"message": "Email verified. You can now log in."})


@auth_bp.route("/resend-verification", methods=["POST"])
@limiter.limit("5 per hour")
def resend_verification():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    # Always return the same generic message whether or not the account
    # exists / is already verified — don't let this endpoint be used to
    # enumerate registered emails.
    generic = {"message": "If an account exists for that email, a verification link has been sent."}

    if user is not None and not user.is_email_verified:
        token = issue_email_verification_token(user.id)
        send_verification_email(user, token)

    return jsonify(generic)


# ---------------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per hour")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember", False))

    user = User.query.filter_by(email=email).first()

    # Constant-shape response whether the email doesn't exist or the
    # password is wrong — never reveal which one it was.
    if user is None or not user.check_password(password):
        return error_response("Invalid email or password.", status=401)

    if not user.is_active_account:
        return error_response("This account has been disabled.", status=403)

    if not user.is_email_verified:
        return error_response(
            "Please verify your email before logging in.", status=403,
            field_errors={"email_verified": False},
        )

    login_user(user, remember=remember)

    resp = jsonify({"message": "Logged in.", "user": user.to_public_dict()})
    # Readable (non-HttpOnly) by design — the frontend must read this
    # cookie to echo it back in the X-CSRF-Token header (see utils/csrf.py).
    resp.set_cookie(
        CSRF_COOKIE_NAME,
        generate_csrf_token(),
        httponly=False,
        samesite=current_app.config["SESSION_COOKIE_SAMESITE"],
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        max_age=int(current_app.config["PERMANENT_SESSION_LIFETIME"].total_seconds()) if remember else None,
    )
    return resp


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    resp = jsonify({"message": "Logged out."})
    resp.delete_cookie(CSRF_COOKIE_NAME)
    return resp


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({"user": current_user.to_public_dict()})


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------
@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    user = User.query.filter_by(email=email).first()
    generic = {"message": "If an account exists for that email, a reset link has been sent."}

    if user is not None:
        token = issue_password_reset_token(user.id)
        send_password_reset_email(user, token)

    return jsonify(generic)


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_password = data.get("password") or ""

    pw_errors = password_errors(new_password)
    if pw_errors:
        return error_response("Password does not meet requirements.", field_errors={"password": pw_errors})

    try:
        user_id = consume_password_reset_token(token)
    except TokenError:
        return error_response("This reset link is invalid or has expired.", status=400)

    user = db.session.get(User, user_id)
    if user is None:
        return error_response("This reset link is invalid or has expired.", status=400)

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "Password has been reset. You can now log in."})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_user.check_password(current_password):
        return error_response("Current password is incorrect.", status=401)

    pw_errors = password_errors(new_password)
    if pw_errors:
        return error_response("Password does not meet requirements.", field_errors={"password": pw_errors})

    current_user.set_password(new_password)
    db.session.commit()
    return jsonify({"message": "Password changed."})
