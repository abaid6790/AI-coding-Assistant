import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class CodeReview(db.Model):
    """Stores the result of a code-review request (Phase 8 feature).
    Schema exists now so the data layer is complete; the route/service
    that populates this comes later.
    """

    __tablename__ = "code_reviews"

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

    language = db.Column(db.String(50), nullable=True)
    source_snapshot = db.Column(db.Text, nullable=False)  # code as it was reviewed
    # Findings stored as JSON: list of {severity, title, description, line}
    findings_json = db.Column(db.Text, nullable=False, default="[]")

    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self, include_source: bool = False) -> dict:
        import json
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "file_id": self.file_id,
            "language": self.language,
            "findings": json.loads(self.findings_json) if self.findings_json else [],
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_source:
            data["source_snapshot"] = self.source_snapshot
        return data
