from flask import current_app, render_template_string
from flask_mail import Message as MailMessage

from extensions import mail

_VERIFY_TEMPLATE = """\
Hi{{ ' ' + name if name else '' }},

Please verify your email address by opening this link (expires in 24 hours):

{{ link }}

If you didn't create an account, you can ignore this email.
"""

_RESET_TEMPLATE = """\
Hi{{ ' ' + name if name else '' }},

We received a request to reset your password. This link expires in 1 hour:

{{ link }}

If you didn't request this, you can safely ignore this email — your
password will not be changed.
"""


def _send(subject: str, recipient: str, body: str) -> None:
    msg = MailMessage(subject=subject, recipients=[recipient], body=body)
    # MAIL_SUPPRESS_SEND (set in config) makes Flask-Mail no-op the actual
    # send and just record it — handy for local dev without SMTP creds.
    # If you've set real credentials and emails still aren't arriving,
    # check this flag first: it must be "false" for anything to actually
    # go out over SMTP, regardless of how correct MAIL_USERNAME/
    # MAIL_PASSWORD are.
    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        current_app.logger.info("[email suppressed] to=%s subject=%s\n%s", recipient, subject, body)
        return

    try:
        mail.send(msg)
    except Exception as exc:
        # A bad app password, wrong MAIL_SERVER/PORT, or an unverified
        # sender address all surface here as an SMTP exception. Logging
        # it explicitly (rather than letting it fall through to the
        # generic 500 handler's less specific message) makes this the
        # first thing you see in the console when debugging why an
        # email didn't arrive.
        current_app.logger.error("Failed to send email to %s via SMTP: %s", recipient, exc)
        raise


def send_verification_email(user, token: str) -> None:
    link = f"{current_app.config['FRONTEND_ORIGIN']}/verify-email?token={token}"
    body = render_template_string(_VERIFY_TEMPLATE, name=user.display_name, link=link)
    _send("Verify your email", user.email, body)


def send_password_reset_email(user, token: str) -> None:
    link = f"{current_app.config['FRONTEND_ORIGIN']}/reset-password?token={token}"
    body = render_template_string(_RESET_TEMPLATE, name=user.display_name, link=link)
    _send("Reset your password", user.email, body)
