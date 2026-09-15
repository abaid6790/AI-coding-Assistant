"""
Review is its own service file (rather than folding into
analysis_service.py) because it's the one feature that persists two
rows — CodeReview (findings) and CodeAnalysis (scores/complexity) —
and has its own fetch-by-id endpoint. Powers the Code Analysis
Dashboard (see api/projects.py's /analysis endpoint) downstream.
"""
import json

from flask import jsonify
from flask_login import current_user

from extensions import db
from models.code_review import CodeReview
from models.code_analysis import CodeAnalysis
from services.ai import prompts as p
from services.ai.parsing import extract_json
from services.code.common import resolve_source, run_ai
from utils.ownership import get_owned_or_404


def create_review(data: dict):
    """Returns (flask_response, None) on success, (None, error_response)
    on failure."""
    resolved, err = resolve_source(data)
    if err:
        return None, err
    code, language, file_, project_id = resolved

    system, user_prompt = p.review_prompt(code, language)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    try:
        parsed = extract_json(ai_response.text)
        findings = parsed.get("findings", [])
        scores = parsed.get("scores", {})
        complexity = parsed.get("complexity")
    except ValueError:
        findings = [{"severity": "Suggestion", "title": "Review", "description": ai_response.text, "line": None}]
        scores = {}
        complexity = None

    code_review = CodeReview(
        user_id=current_user.id,
        project_id=project_id,
        file_id=file_.id if file_ else None,
        language=language,
        source_snapshot=code,
        findings_json=json.dumps(findings),
        provider=ai_response.provider,
        model=ai_response.model,
    )
    db.session.add(code_review)

    code_analysis = CodeAnalysis(
        user_id=current_user.id,
        project_id=project_id,
        file_id=file_.id if file_ else None,
        quality_score=scores.get("quality"),
        security_score=scores.get("security"),
        performance_score=scores.get("performance"),
        maintainability_score=scores.get("maintainability"),
        complexity_summary=complexity,
    )
    db.session.add(code_analysis)
    db.session.commit()

    response = jsonify({
        "review_id": code_review.id,
        "findings": findings,
        "scores": scores,
        "complexity": code_analysis.complexity_summary,
        "provider": ai_response.provider,
        "model": ai_response.model,
    })
    return (response, 201), None


def get_review(review_id: str):
    """Raises via Flask's abort(404) internally (get_owned_or_404) if
    the review doesn't exist or isn't the caller's — no error tuple
    needed here since that short-circuits the request on its own."""
    review_row = get_owned_or_404(CodeReview, review_id)
    return jsonify({
        "id": review_row.id,
        "language": review_row.language,
        "findings": json.loads(review_row.findings_json),
        "created_at": review_row.created_at.isoformat() if review_row.created_at else None,
    })
