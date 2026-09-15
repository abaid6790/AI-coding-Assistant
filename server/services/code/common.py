"""
Shared by analysis_service.py, review_service.py, and generation_service.py
so the source-resolution and AI-call-with-error-handling logic exists in
one place rather than being duplicated three times.
"""
from flask import current_app

from models.project import Project
from models.project_file import ProjectFile
from utils.ownership import get_owned_or_404
from utils.validation import error_response
from services.ai.base import AIProviderError, AIProviderUnavailable
from services.ai.service import AIService


def resolve_source(data: dict):
    """Returns ((code, language, file_or_None, project_id_or_None), None)
    on success, or (None, error_response) on failure."""
    file_id = data.get("file_id")
    project_id = data.get("project_id")
    code = data.get("code")
    language = data.get("language")
    file_ = None

    if file_id:
        file_ = get_owned_or_404(ProjectFile, file_id)
        if project_id and file_.project_id != project_id:
            return None, error_response("file_id does not belong to project_id.", status=400)
        project_id = file_.project_id
        if code is None:
            code = file_.content
        if language is None:
            language = file_.language
    elif project_id:
        # No file, but a project was named — confirm it's actually theirs
        # before letting a review/test/doc row attach to it.
        get_owned_or_404(Project, project_id)

    if not code or not code.strip():
        return None, error_response("Code is required (provide 'code' or 'file_id').", field_errors={"code": "required"})

    return (code, language, file_, project_id), None


def run_ai(system: str, user_prompt: str, provider_name: str | None = None):
    """Returns (AIResponse, None) on success, or (None, error_response) on
    a provider failure — the two AIService exception types map to
    distinct HTTP statuses so the frontend can tell "try again shortly"
    apart from "rephrase your request"."""
    ai_service = AIService(current_app.config)
    try:
        return ai_service.generate(user_prompt, provider=provider_name, system=system), None
    except AIProviderUnavailable as exc:
        current_app.logger.warning("AI provider unavailable: %s", exc)
        return None, error_response(
            "The AI assistant is temporarily unavailable. Please try again shortly.", status=503,
        )
    except AIProviderError as exc:
        current_app.logger.error("AI provider error: %s", exc)
        return None, error_response(
            "The AI assistant couldn't process that request. Please try again.", status=502,
        )
