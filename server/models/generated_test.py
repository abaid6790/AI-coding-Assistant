import uuid
from datetime import datetime, timezone

from extensions import db


def _uuid():
    return str(uuid.uuid4())


class GeneratedTest(db.Model):
    __tablename__ = "generated_tests"

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

    framework = db.Column(db.String(50), nullable=True)  # pytest | unittest | jest | mocha | junit
    source_snapshot = db.Column(db.Text, nullable=False)
    generated_code = db.Column(db.Text, nullable=False)

    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self, include_code: bool = False) -> dict:
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "file_id": self.file_id,
            "framework": self.framework,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_code:
            data["generated_code"] = self.generated_code
        return data
