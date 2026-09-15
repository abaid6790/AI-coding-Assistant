"""
Phase 8's seven code-intelligence routes. Each route follows the same
five-line shape: parse the request body, call the matching service
function, return its result or its error. All the actual logic — source
resolution, prompt building, calling AIService, parsing the response,
and persisting where the schema calls for it — lives in
services/code/{common,analysis_service,review_service,generation_service}.py.

None of this executes user-submitted code — these are all AI text
generations about code, never a code execution sandbox (see spec:
"Never execute arbitrary user-submitted code on the backend").
"""
from flask import Blueprint, request
from flask_login import login_required

from extensions import limiter
from services.code import analysis_service, review_service, generation_service

code_bp = Blueprint("code", __name__, url_prefix="/api/code")


@code_bp.route("/explain", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def explain():
    data = request.get_json(silent=True) or {}
    result, err = analysis_service.explain_code(data)
    return err if err else result


@code_bp.route("/generate", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def generate():
    data = request.get_json(silent=True) or {}
    result, err = generation_service.generate_code(data)
    return err if err else result


@code_bp.route("/debug", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def debug():
    data = request.get_json(silent=True) or {}
    result, err = analysis_service.debug_code(data)
    return err if err else result


@code_bp.route("/review", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def review():
    data = request.get_json(silent=True) or {}
    result, err = review_service.create_review(data)
    return err if err else result


@code_bp.route("/reviews/<review_id>", methods=["GET"])
@login_required
def get_review(review_id):
    return review_service.get_review(review_id)


@code_bp.route("/optimize", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def optimize():
    data = request.get_json(silent=True) or {}
    result, err = generation_service.optimize_code(data)
    return err if err else result


@code_bp.route("/tests", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def generate_tests():
    data = request.get_json(silent=True) or {}
    result, err = generation_service.generate_tests(data)
    return err if err else result


@code_bp.route("/documentation", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def generate_documentation():
    data = request.get_json(silent=True) or {}
    result, err = generation_service.generate_documentation(data)
    return err if err else result
