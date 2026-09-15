"""
Project, file, folder, and code-intelligence-history routes. Each route
parses the request (query args / JSON body / URL params), calls the
matching function in services/projects/project_service.py, and returns
its result. See that module's docstring for the full behavior.
"""
from flask import Blueprint, request
from flask_login import login_required

from extensions import limiter
from services.projects import project_service

projects_bp = Blueprint("projects", __name__, url_prefix="/api/projects")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
@projects_bp.route("", methods=["GET"])
@login_required
def list_projects():
    return project_service.list_projects(request.args.get("search"))


@projects_bp.route("", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def create_project():
    data = request.get_json(silent=True) or {}
    result, err = project_service.create_project(data)
    return err if err else result


@projects_bp.route("/<project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    return project_service.get_project(project_id)


@projects_bp.route("/<project_id>", methods=["PATCH"])
@login_required
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    result, err = project_service.update_project(project_id, data)
    return err if err else result


@projects_bp.route("/<project_id>", methods=["DELETE"])
@login_required
def delete_project(project_id):
    return project_service.delete_project(project_id)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
@projects_bp.route("/<project_id>/files", methods=["GET"])
@login_required
def list_files(project_id):
    return project_service.list_files(project_id, request.args.get("search"), request.args.get("folder"))


@projects_bp.route("/<project_id>/files", methods=["POST"])
@login_required
@limiter.limit("120 per hour")
def create_file(project_id):
    data = request.get_json(silent=True) or {}
    result, err = project_service.create_file(project_id, data)
    return err if err else result


@projects_bp.route("/<project_id>/files/<file_id>", methods=["GET"])
@login_required
def get_file(project_id, file_id):
    return project_service.get_file(project_id, file_id)


@projects_bp.route("/<project_id>/files/<file_id>", methods=["PATCH"])
@login_required
def update_file(project_id, file_id):
    data = request.get_json(silent=True) or {}
    result, err = project_service.update_file(project_id, file_id, data)
    return err if err else result


@projects_bp.route("/<project_id>/files/<file_id>", methods=["DELETE"])
@login_required
def delete_file(project_id, file_id):
    return project_service.delete_file(project_id, file_id)


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
@projects_bp.route("/<project_id>/folders", methods=["GET"])
@login_required
def list_folders(project_id):
    return project_service.list_folders(project_id)


@projects_bp.route("/<project_id>/folders", methods=["PATCH"])
@login_required
def rename_folder(project_id):
    data = request.get_json(silent=True) or {}
    result, err = project_service.rename_folder(project_id, data)
    return err if err else result


# ---------------------------------------------------------------------------
# Code-intelligence history + analysis dashboard (Phase 9)
# ---------------------------------------------------------------------------
@projects_bp.route("/<project_id>/reviews", methods=["GET"])
@login_required
def list_project_reviews(project_id):
    return project_service.list_project_reviews(project_id)


@projects_bp.route("/<project_id>/tests", methods=["GET"])
@login_required
def list_project_tests(project_id):
    return project_service.list_project_tests(project_id)


@projects_bp.route("/<project_id>/tests/<test_id>", methods=["GET"])
@login_required
def get_project_test(project_id, test_id):
    return project_service.get_project_test(project_id, test_id)


@projects_bp.route("/<project_id>/documents", methods=["GET"])
@login_required
def list_project_documents(project_id):
    return project_service.list_project_documents(project_id)


@projects_bp.route("/<project_id>/documents/<document_id>", methods=["GET"])
@login_required
def get_project_document(project_id, document_id):
    return project_service.get_project_document(project_id, document_id)


@projects_bp.route("/<project_id>/analysis", methods=["GET"])
@login_required
def get_project_analysis(project_id):
    return project_service.get_project_analysis(project_id)
