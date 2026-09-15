import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class ProjectFile(db.Model):
    __tablename__ = "project_files"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    project_id = db.Column(
        db.String(36), db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Denormalized owner id — lets us scope "is this file mine?" queries
    # with a single indexed column instead of a join, everywhere in the app.
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    filename = db.Column(db.String(255), nullable=False)
    # Virtual folder path within the project, e.g. "src/utils". Empty = root.
    folder_path = db.Column(db.String(500), nullable=False, default="")
    language = db.Column(db.String(50), nullable=True)
    content = db.Column(db.Text, nullable=False, default="")
    size_bytes = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_files_project_folder", "project_id", "folder_path"),
        db.UniqueConstraint("project_id", "folder_path", "filename", name="uq_file_path"),
    )

    def to_dict(self, include_content: bool = False) -> dict:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "filename": self.filename,
            "folder_path": self.folder_path,
            "language": self.language,
            "size_bytes": self.size_bytes,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            data["content"] = self.content
        return data
