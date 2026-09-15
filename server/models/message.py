import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = db.Column(db.String(20), nullable=False)  # "user" | "assistant" | "system"
    content = db.Column(db.Text, nullable=False)

    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
