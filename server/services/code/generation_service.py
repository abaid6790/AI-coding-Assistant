"""
The four "produce something" code-intelligence features. Generate and
Optimize are ephemeral (no dedicated table — see Phase 1's schema);
Tests and Documentation persist to GeneratedTest/Document respectively.
"""
from flask import jsonify
from flask_login import current_user

from extensions import db
from models.generated_test import GeneratedTest
from models.document import Document
from utils.validation import error_response
from services.ai import prompts as p
from services.ai.parsing import extract_json, extract_code_block
from services.code.common import resolve_source, run_ai


def generate_code(data: dict):
    description = (data.get("description") or "").strip()
    language = data.get("language")

    if not description:
        return None, error_response("A description is required.", field_errors={"description": "required"})

    system, user_prompt = p.generate_prompt(description, language)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    try:
        parsed = extract_json(ai_response.text)
        code = parsed.get("code", "")
        explanation = parsed.get("explanation", "")
    except ValueError:
        # Model didn't follow the JSON instruction — fall back to
        # pulling a code block out of the raw text rather than failing
        # the whole request over a formatting slip.
        code = extract_code_block(ai_response.text)
        explanation = ai_response.text

    return jsonify({
        "code": code, "explanation": explanation,
        "provider": ai_response.provider, "model": ai_response.model,
    }), None


def optimize_code(data: dict):
    resolved, err = resolve_source(data)
    if err:
        return None, err
    code, language, _file, _project_id = resolved

    system, user_prompt = p.optimize_prompt(code, language)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    try:
        parsed = extract_json(ai_response.text)
        optimized_code = parsed.get("optimized_code", "")
        explanation = parsed.get("explanation", "")
    except ValueError:
        optimized_code = extract_code_block(ai_response.text)
        explanation = ai_response.text

    return jsonify({
        "original_code": code,
        "optimized_code": optimized_code,
        "explanation": explanation,
        "provider": ai_response.provider,
        "model": ai_response.model,
    }), None


def generate_tests(data: dict):
    resolved, err = resolve_source(data)
    if err:
        return None, err
    code, language, file_, project_id = resolved
    framework = data.get("framework") or "pytest"

    system, user_prompt = p.tests_prompt(code, language, framework)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    generated_code = extract_code_block(ai_response.text)

    generated_test = GeneratedTest(
        user_id=current_user.id,
        project_id=project_id,
        file_id=file_.id if file_ else None,
        framework=framework,
        source_snapshot=code,
        generated_code=generated_code,
        provider=ai_response.provider,
        model=ai_response.model,
    )
    db.session.add(generated_test)
    db.session.commit()

    response = jsonify({
        "test_id": generated_test.id,
        "framework": framework,
        "generated_code": generated_code,
        "provider": ai_response.provider,
        "model": ai_response.model,
    })
    return (response, 201), None


def generate_documentation(data: dict):
    resolved, err = resolve_source(data)
    if err:
        return None, err
    code, language, file_, project_id = resolved
    doc_type = data.get("doc_type") or "docstring"

    system, user_prompt = p.documentation_prompt(code, language, doc_type)
    ai_response, err = run_ai(system, user_prompt, data.get("provider"))
    if err:
        return None, err

    document = Document(
        user_id=current_user.id,
        project_id=project_id,
        file_id=file_.id if file_ else None,
        doc_type=doc_type,
        title=data.get("title"),
        content=ai_response.text,
        provider=ai_response.provider,
        model=ai_response.model,
    )
    db.session.add(document)
    db.session.commit()

    response = jsonify({
        "document_id": document.id,
        "doc_type": doc_type,
        "content": ai_response.text,
        "provider": ai_response.provider,
        "model": ai_response.model,
    })
    return (response, 201), None
