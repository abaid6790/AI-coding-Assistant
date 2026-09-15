import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class CodeAnalysis(db.Model):
    """Aggregate scores shown on the Code Analysis Dashboard (Phase 9).
    AI-assisted estimates, not authoritative — surfaced as such in the UI.
    """

    __tablename__ = "code_analyses"

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

    quality_score = db.Column(db.Integer, nullable=True)
    security_score = db.Column(db.Integer, nullable=True)
    performance_score = db.Column(db.Integer, nullable=True)
    maintainability_score = db.Column(db.Integer, nullable=True)
    complexity_summary = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "file_id": self.file_id,
            "quality_score": self.quality_score,
            "security_score": self.security_score,
            "performance_score": self.performance_score,
            "maintainability_score": self.maintainability_score,
            "complexity_summary": self.complexity_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
