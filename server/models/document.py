import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class Document(db.Model):
    """Generated documentation (docstrings, README sections, API docs)."""

    __tablename__ = "documents"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = db.Column(
        db.String(36), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    file_id = db.Column(
        db.String(36), db.ForeignKey("project_files.id", ondelete="SET NULL"), nullable=True
    )

    doc_type = db.Column(db.String(50), nullable=True)  # docstring | readme | api_docs | comments
    title = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)

    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self, include_content: bool = False) -> dict:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "file_id": self.file_id,
            "doc_type": self.doc_type,
            "title": self.title,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_content:
            data["content"] = self.content
        return data
