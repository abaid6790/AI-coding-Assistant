import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    files = db.relationship(
        "ProjectFile", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )
    conversations = db.relationship(
        "Conversation", backref="project", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.Index("ix_projects_user_updated", "user_id", "updated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
