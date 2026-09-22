"""
Phase 8's seven code-intelligence routes, plus Phase 13's Run Code
route. Each route follows the same five-line shape: parse the request
body, call the matching service function, return its result or its
error. All the actual logic — source resolution, prompt building,
calling AIService, parsing the response, and persisting where the
schema calls for it — lives in
services/code/{common,analysis_service,review_service,generation_service,execution_service}.py.

The seven AI features never execute user-submitted code — those are
all AI text generations about code. /run is the one exception: it
executes code, but always in a separate OS process via services/
execution/ (see that package's docstring for the safety model), never
via exec()/eval() inside this Flask process.
"""
from flask import Blueprint, request
from flask_login import login_required

from extensions import limiter
from services.code import analysis_service, review_service, generation_service, execution_service

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


@code_bp.route("/run", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def run():
    # More generous than the AI endpoints above (which cost real money
    # per call) since running code is meant to be iterated on quickly
    # — write, run, see the error, fix, run again. Still bounded: each
    # individual run is capped at 10s wall-clock and ~200KB of output
    # regardless of this rate limit (see services/execution/common.py).
    data = request.get_json(silent=True) or {}
    result, err = execution_service.execute_code(data)
    return err if err else result
