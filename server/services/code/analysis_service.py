"""
Explain and Debug: both are "understand what this code does or why it's
failing" features, as opposed to generation_service.py's "produce new or
modified code" features. Neither persists to a table — see Phase 1's
schema, which only has tables for reviews/tests/documents.
"""
from flask import jsonify

from services.ai import prompts as p
from services.ai.parsing import extract_json
from services.code.common import resolve_source, run_ai


def explain_code(data: dict):
    """Returns (flask_response, None) on success, (None, error_response)
    on failure — the route just returns whichever isn't None."""
    resolved, err = resolve_source(data)
    if err:
        return None, err
    code, language, _file, _project_id = resolved

    system, user_prompt = p.explain_prompt(code, language)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    return jsonify({
        "explanation": ai_response.text, "provider": ai_response.provider, "model": ai_response.model,
    }), None


def debug_code(data: dict):
    resolved, err = resolve_source(data)
    if err:
        return None, err
    code, language, _file, _project_id = resolved

    error_message = data.get("error_message", "")
    stack_trace = data.get("stack_trace", "")

    system, user_prompt = p.debug_prompt(code, error_message, stack_trace, language)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    try:
        parsed = extract_json(ai_response.text)
    except ValueError:
        parsed = {
            "likely_cause": None, "problematic_code": None,
            "suggested_fix": None, "corrected_code": None,
            "explanation": ai_response.text,
        }

    parsed["is_suggestion"] = True  # always labeled a suggestion, never a guaranteed fix
    parsed["provider"] = ai_response.provider
    parsed["model"] = ai_response.model
    return jsonify(parsed), None
