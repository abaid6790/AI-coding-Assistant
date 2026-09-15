"""
Business logic for projects, files, virtual folders, and the read-only
code-intelligence history/analysis views. api/projects.py's routes are
thin wrappers around these functions — see that file's docstring for
the request/response contract each follows.

Files are organized into virtual folders via `ProjectFile.folder_path`
— there's no separate Folder table, so an empty folder only exists as
long as at least one file references its path (same limitation most
editors built on flat storage have). Folder rename bulk-updates every
file under that path.

The ownership pattern from Phase 3 (utils/ownership.py) is unchanged
and reused by every function below.
"""
from flask import jsonify, current_app, abort
from flask_login import current_user

from extensions import db
from models.project import Project
from models.project_file import ProjectFile
from models.code_review import CodeReview
from models.code_analysis import CodeAnalysis
from models.generated_test import GeneratedTest
from models.document import Document
from utils.ownership import get_owned_or_404, owned_query
from utils.validation import (
    error_response,
    is_valid_filename,
    is_valid_folder_path,
    validate_file_extension,
)

MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB per file, matches typical editor limits


def _get_owned_file_in_project(project_id, file_id):
    """A file must belong to BOTH the current user AND the project named
    in the URL — see Phase 3 notes on why the second check matters even
    once the first one passes."""
    file_ = get_owned_or_404(ProjectFile, file_id)
    if file_.project_id != project_id:
        abort(404)
    return file_


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def list_projects(search: str = ""):
    query = owned_query(Project)
    search = (search or "").strip()
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    projects = query.order_by(Project.updated_at.desc()).all()
    return jsonify({"projects": [p.to_dict() for p in projects]})


def create_project(data: dict):
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip() or None

    if not name:
        return None, error_response("Project name is required.", field_errors={"name": "required"})
    if len(name) > 200:
        return None, error_response("Project name is too long.", field_errors={"name": "max_length"})

    project = Project(user_id=current_user.id, name=name, description=description)
    db.session.add(project)
    db.session.commit()
    return (jsonify({"project": project.to_dict()}), 201), None


def get_project(project_id: str):
    project = get_owned_or_404(Project, project_id)
    return jsonify({"project": project.to_dict()})


def update_project(project_id: str, data: dict):
    project = get_owned_or_404(Project, project_id)

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return None, error_response("Project name cannot be empty.", field_errors={"name": "required"})
        if len(name) > 200:
            return None, error_response("Project name is too long.", field_errors={"name": "max_length"})
        project.name = name

    if "description" in data:
        project.description = (data["description"] or "").strip() or None

    db.session.commit()
    return jsonify({"project": project.to_dict()}), None


def delete_project(project_id: str):
    project = get_owned_or_404(Project, project_id)
    db.session.delete(project)  # cascades to files/conversations via model relationships
    db.session.commit()
    return jsonify({"message": "Project deleted."})


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
def list_files(project_id: str, search: str = "", folder: str | None = None):
    get_owned_or_404(Project, project_id)  # 404s if the project isn't yours

    query = owned_query(ProjectFile).filter_by(project_id=project_id)

    search = (search or "").strip()
    if search:
        query = query.filter(ProjectFile.filename.ilike(f"%{search}%"))

    if folder is not None:
        query = query.filter(ProjectFile.folder_path == folder)

    files = query.order_by(ProjectFile.folder_path, ProjectFile.filename).all()
    return jsonify({"files": [f.to_dict() for f in files]})


def create_file(project_id: str, data: dict):
    project = get_owned_or_404(Project, project_id)
    filename = (data.get("filename") or "").strip()
    folder_path = (data.get("folder_path") or "").strip().strip("/")
    content = data.get("content") or ""
    language = data.get("language")

    if not filename:
        return None, error_response("Filename is required.", field_errors={"filename": "required"})
    if not is_valid_filename(filename):
        return None, error_response(
            "Filename contains characters that aren't allowed.", field_errors={"filename": "invalid"}
        )
    if not is_valid_folder_path(folder_path):
        return None, error_response(
            "Folder path contains characters that aren't allowed.", field_errors={"folder_path": "invalid"}
        )
    if not validate_file_extension(filename, current_app.config["ALLOWED_FILE_EXTENSIONS"]):
        return None, error_response(
            "That file type isn't supported.", field_errors={"filename": "extension_not_allowed"}
        )
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        return None, error_response("File is too large.", field_errors={"content": "max_size"})

    existing = ProjectFile.query.filter_by(
        project_id=project.id, folder_path=folder_path, filename=filename
    ).first()
    if existing is not None:
        return None, error_response(
            "A file with that name already exists in this folder.", status=409,
            field_errors={"filename": "duplicate"},
        )

    file_ = ProjectFile(
        project_id=project.id,
        user_id=current_user.id,
        filename=filename,
        folder_path=folder_path,
        language=language,
        content=content,
        size_bytes=len(content.encode("utf-8")),
    )
    db.session.add(file_)
    db.session.commit()
    return (jsonify({"file": file_.to_dict(include_content=True)}), 201), None


def get_file(project_id: str, file_id: str):
    get_owned_or_404(Project, project_id)
    file_ = _get_owned_file_in_project(project_id, file_id)
    return jsonify({"file": file_.to_dict(include_content=True)})


def update_file(project_id: str, file_id: str, data: dict):
    """Rename, move to a different folder, change language, or edit content."""
    get_owned_or_404(Project, project_id)
    file_ = _get_owned_file_in_project(project_id, file_id)

    new_filename = file_.filename
    new_folder = file_.folder_path

    if "filename" in data:
        new_filename = (data["filename"] or "").strip()
        if not new_filename:
            return None, error_response("Filename cannot be empty.", field_errors={"filename": "required"})
        if not is_valid_filename(new_filename):
            return None, error_response(
                "Filename contains characters that aren't allowed.", field_errors={"filename": "invalid"}
            )

    if "folder_path" in data:
        new_folder = (data["folder_path"] or "").strip().strip("/")
        if not is_valid_folder_path(new_folder):
            return None, error_response(
                "Folder path contains characters that aren't allowed.", field_errors={"folder_path": "invalid"}
            )

    if new_filename != file_.filename and not validate_file_extension(
        new_filename, current_app.config["ALLOWED_FILE_EXTENSIONS"]
    ):
        return None, error_response(
            "That file type isn't supported.", field_errors={"filename": "extension_not_allowed"}
        )

    if (new_filename, new_folder) != (file_.filename, file_.folder_path):
        clash = ProjectFile.query.filter(
            ProjectFile.project_id == project_id,
            ProjectFile.folder_path == new_folder,
            ProjectFile.filename == new_filename,
            ProjectFile.id != file_.id,
        ).first()
        if clash is not None:
            return None, error_response(
                "A file with that name already exists in this folder.", status=409,
                field_errors={"filename": "duplicate"},
            )
        file_.filename = new_filename
        file_.folder_path = new_folder

    if "language" in data:
        file_.language = data["language"]

    if "content" in data:
        content = data["content"] or ""
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            return None, error_response("File is too large.", field_errors={"content": "max_size"})
        file_.content = content
        file_.size_bytes = len(content.encode("utf-8"))

    db.session.commit()
    return jsonify({"file": file_.to_dict(include_content=True)}), None


def delete_file(project_id: str, file_id: str):
    get_owned_or_404(Project, project_id)
    file_ = _get_owned_file_in_project(project_id, file_id)
    db.session.delete(file_)
    db.session.commit()
    return jsonify({"message": "File deleted."})


# ---------------------------------------------------------------------------
# Folders — virtual: derived from, and renamed via, ProjectFile.folder_path
# ---------------------------------------------------------------------------
def list_folders(project_id: str):
    get_owned_or_404(Project, project_id)
    rows = (
        owned_query(ProjectFile)
        .filter_by(project_id=project_id)
        .with_entities(ProjectFile.folder_path)
        .distinct()
        .all()
    )
    folders = sorted({r[0] for r in rows if r[0]})
    return jsonify({"folders": folders})


def rename_folder(project_id: str, data: dict):
    """Bulk-renames a folder by rewriting folder_path on every file under
    it. Body: {"old_path": "src/utils", "new_path": "src/helpers"}."""
    get_owned_or_404(Project, project_id)
    old_path = (data.get("old_path") or "").strip().strip("/")
    new_path = (data.get("new_path") or "").strip().strip("/")

    if not old_path or not new_path:
        return None, error_response("Both old_path and new_path are required.")
    if not is_valid_folder_path(new_path):
        return None, error_response(
            "Folder path contains characters that aren't allowed.", field_errors={"new_path": "invalid"}
        )

    files = owned_query(ProjectFile).filter_by(project_id=project_id).filter(
        (ProjectFile.folder_path == old_path) | ProjectFile.folder_path.like(f"{old_path}/%")
    ).all()

    if not files:
        return None, error_response("No files found under that folder.", status=404)

    for f in files:
        if f.folder_path == old_path:
            f.folder_path = new_path
        else:
            f.folder_path = new_path + f.folder_path[len(old_path):]

    db.session.commit()
    return jsonify({"message": f"Renamed {len(files)} file(s).", "moved": len(files)}), None


# ---------------------------------------------------------------------------
# Code-intelligence history (Phase 9) — read-only lists of what Phase 8's
# review/tests/documentation endpoints have persisted for this project,
# plus an aggregated view for the Code Analysis Dashboard.
# ---------------------------------------------------------------------------
def list_project_reviews(project_id: str):
    get_owned_or_404(Project, project_id)
    reviews = (
        owned_query(CodeReview)
        .filter_by(project_id=project_id)
        .order_by(CodeReview.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"reviews": [r.to_dict() for r in reviews]})


def list_project_tests(project_id: str):
    get_owned_or_404(Project, project_id)
    tests = (
        owned_query(GeneratedTest)
        .filter_by(project_id=project_id)
        .order_by(GeneratedTest.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"tests": [t.to_dict() for t in tests]})


def get_project_test(project_id: str, test_id: str):
    get_owned_or_404(Project, project_id)
    test_ = get_owned_or_404(GeneratedTest, test_id)
    if test_.project_id != project_id:
        abort(404)
    return jsonify({"test": test_.to_dict(include_code=True)})


def list_project_documents(project_id: str):
    get_owned_or_404(Project, project_id)
    documents = (
        owned_query(Document)
        .filter_by(project_id=project_id)
        .order_by(Document.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"documents": [d.to_dict() for d in documents]})


def get_project_document(project_id: str, document_id: str):
    get_owned_or_404(Project, project_id)
    document = get_owned_or_404(Document, document_id)
    if document.project_id != project_id:
        abort(404)
    return jsonify({"document": document.to_dict(include_content=True)})


def get_project_analysis(project_id: str):
    """Aggregated view for the Code Analysis Dashboard: the most recent
    scores, a short history for a trend view, and the issue-severity
    breakdown from the most recent review. All AI-assisted estimates —
    surfaced as such in the UI, never as an authoritative certification."""
    get_owned_or_404(Project, project_id)

    history = (
        owned_query(CodeAnalysis)
        .filter_by(project_id=project_id)
        .order_by(CodeAnalysis.created_at.desc())
        .limit(10)
        .all()
    )
    latest_review = (
        owned_query(CodeReview)
        .filter_by(project_id=project_id)
        .order_by(CodeReview.created_at.desc())
        .first()
    )

    latest = history[0].to_dict() if history else None
    findings = latest_review.to_dict()["findings"] if latest_review else []
    severity_counts = {}
    for f in findings:
        sev = f.get("severity", "Suggestion")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return jsonify({
        "latest": latest,
        "history": [h.to_dict() for h in reversed(history)],  # chronological for a trend view
        "issues_found": len(findings),
        "issues_by_severity": severity_counts,
        "reviews_count": owned_query(CodeReview).filter_by(project_id=project_id).count(),
        "tests_count": owned_query(GeneratedTest).filter_by(project_id=project_id).count(),
        "documents_count": owned_query(Document).filter_by(project_id=project_id).count(),
    })
