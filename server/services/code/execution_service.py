"""
The Run Code feature (spec sections 2-4, 8). Unlike every other
function in services/code/, a "failed" run — a syntax error, a runtime
exception, a timeout — is NOT an error response here. The request
itself succeeded; the CODE being run didn't. That's a 200 with
success: false in the body, matching the spec's exact envelope, not an
HTTP error status.

Real (result, err) failures — matching the same contract every other
services/code/ function uses — are reserved for things actually wrong
with the REQUEST: missing code, or an unsupported language.

No persistence here (see spec section 11's scope: no run history, no
cloud storage) — this is intentionally the simplest function in
services/code/.
"""
from flask import jsonify

from services.execution import run_code, SUPPORTED_LANGUAGES, ExecutionCapacityError
from utils.validation import error_response


def execute_code(data: dict):
    """Returns (flask_response, None) for ANY execution outcome —
    success or a failed run both return 200 with the result envelope —
    or (None, error_response) if the request itself is invalid or the
    server is at capacity."""
    language = (data.get("language") or "").strip().lower()
    code = data.get("code")

    if not code or not code.strip():
        return None, error_response("Code is required.", field_errors={"code": "required"})

    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        return None, error_response(
            f"Unsupported language '{language}'. Supported: {supported}.",
            field_errors={"language": "unsupported"},
        )

    try:
        result = run_code(language, code)
    except ExecutionCapacityError:
        # Deliberately NOT part of the run envelope (success: false) —
        # this isn't a code-execution outcome, it's the server saying
        # "I can't even attempt this right now." A real 503 lets the
        # frontend distinguish "your code has a bug" from "try again in
        # a moment" instead of conflating the two.
        return None, error_response(
            "The server is currently running too many programs at once. Please try again in a moment.",
            status=503,
        )

    return jsonify({
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        # Extra fields beyond the spec's base envelope — additive only,
        # so the frontend can show a specific "timed out" / "output
        # truncated" state instead of a generic failure message (the
        # spec explicitly wants timeout/failure states clearly
        # distinguished from an ordinary runtime error).
        "timed_out": result.timed_out,
        "truncated": result.truncated,
    }), None
