import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Nullable: a conversation can exist outside any project ("scratch chat").
    project_id = db.Column(
        db.String(36), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )

    title = db.Column(db.String(255), nullable=False, default="New conversation")
    language = db.Column(db.String(50), nullable=True)
    provider = db.Column(db.String(50), nullable=True)  # e.g. "gemini"
    model = db.Column(db.String(100), nullable=True)  # e.g. "gemini-1.5-flash"

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages = db.relationship(
        "Message",
        backref="conversation",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        db.Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "language": self.language,
            "provider": self.provider,
            "model": self.model,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
