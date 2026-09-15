import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=True)

    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships — every child row cascades on user delete so we never
    # orphan another user's-visible data by accident.
    projects = db.relationship(
        "Project", backref="owner", lazy="dynamic", cascade="all, delete-orphan"
    )
    conversations = db.relationship(
        "Conversation", backref="owner", lazy="dynamic", cascade="all, delete-orphan"
    )
    email_tokens = db.relationship(
        "EmailVerificationToken", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    reset_tokens = db.relationship(
        "PasswordResetToken", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    # Flask-Login required overrides -------------------------------------
    def get_id(self):
        return self.id

    @property
    def is_active(self):
        return self.is_active_account

    # Password helpers -----------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_public_dict(self) -> dict:
        """Safe-to-serialize view of a user — never include password_hash."""
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "is_email_verified": self.is_email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.email}>"
