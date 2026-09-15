import json
from unittest.mock import patch

from tests.conftest import register_and_verify, login_as
from services.ai.base import AIResponse, AIProviderUnavailable


def _create_project(client, name="P"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["project"]


def _create_file(client, project_id, filename="app.py", content="def add(a, b):\n    return a + b"):
    resp = client.post(f"/api/projects/{project_id}/files", json={"filename": filename, "content": content, "language": "python"})
    assert resp.status_code == 201
    return resp.get_json()["file"]


def _mock_ai(text, provider="gemini", model="m"):
    return patch(
        "services.ai.service.AIService.generate",
        return_value=AIResponse(text=text, provider=provider, model=model),
    )


# ---------------------------------------------------------------------------
# Source resolution shared by most endpoints
# ---------------------------------------------------------------------------
def test_explain_requires_code_or_file(client):
    register_and_verify(client, "code1@example.com")
    login_as(client, "code1@example.com")

    resp = client.post("/api/code/explain", json={})
    assert resp.status_code == 400


def test_explain_with_direct_code(client):
    register_and_verify(client, "code2@example.com")
    login_as(client, "code2@example.com")

    with _mock_ai("## Overall explanation\nThis adds two numbers."):
        resp = client.post("/api/code/explain", json={"code": "def add(a,b): return a+b", "language": "python"})

    assert resp.status_code == 200
    assert "adds two numbers" in resp.get_json()["explanation"]


def test_explain_loads_code_from_owned_file(client):
    register_and_verify(client, "code3@example.com")
    login_as(client, "code3@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"], content="def multiply(a, b): return a * b")

    with patch("services.ai.service.AIService.generate") as mock_generate:
        mock_generate.return_value = AIResponse(text="explanation text", provider="gemini", model="m")
        resp = client.post("/api/code/explain", json={"file_id": file_["id"]})

    assert resp.status_code == 200
    prompt_arg = mock_generate.call_args[0][0]
    assert "def multiply(a, b): return a * b" in prompt_arg


def test_explain_rejects_file_from_different_project_than_given(client):
    register_and_verify(client, "code4@example.com")
    login_as(client, "code4@example.com")
    project_a = _create_project(client, "A")
    project_b = _create_project(client, "B")
    file_a = _create_file(client, project_a["id"])

    resp = client.post("/api/code/explain", json={"file_id": file_a["id"], "project_id": project_b["id"]})
    assert resp.status_code == 400


def test_provider_unavailable_returns_503(client):
    register_and_verify(client, "code5@example.com")
    login_as(client, "code5@example.com")

    with patch("services.ai.service.AIService.generate", side_effect=AIProviderUnavailable("no keys")):
        resp = client.post("/api/code/explain", json={"code": "x = 1"})
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------
def test_generate_parses_json_response(client):
    register_and_verify(client, "code6@example.com")
    login_as(client, "code6@example.com")

    payload = json.dumps({"code": "print('hi')", "explanation": "prints hi"})
    with _mock_ai(payload):
        resp = client.post("/api/code/generate", json={"description": "print hi", "language": "python"})

    body = resp.get_json()
    assert body["code"] == "print('hi')"
    assert body["explanation"] == "prints hi"


def test_generate_falls_back_when_response_is_not_json(client):
    register_and_verify(client, "code7@example.com")
    login_as(client, "code7@example.com")

    with _mock_ai("Here you go:\n```python\nprint('hi')\n```\nThat's it."):
        resp = client.post("/api/code/generate", json={"description": "print hi"})

    body = resp.get_json()
    assert body["code"] == "print('hi')"


def test_generate_requires_description(client):
    register_and_verify(client, "code8@example.com")
    login_as(client, "code8@example.com")
    resp = client.post("/api/code/generate", json={})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
def test_debug_parses_structured_response(client):
    register_and_verify(client, "code9@example.com")
    login_as(client, "code9@example.com")

    payload = json.dumps({
        "likely_cause": "off by one", "problematic_code": "range(n)",
        "suggested_fix": "use range(n+1)", "corrected_code": "range(n+1)",
        "explanation": "loop was short by one iteration",
    })
    with _mock_ai(payload):
        resp = client.post("/api/code/debug", json={
            "code": "for i in range(n): pass", "error_message": "wrong count", "language": "python",
        })

    body = resp.get_json()
    assert body["likely_cause"] == "off by one"
    assert body["is_suggestion"] is True


def test_debug_falls_back_to_explanation_on_bad_json(client):
    register_and_verify(client, "code10@example.com")
    login_as(client, "code10@example.com")

    with _mock_ai("Not JSON at all, just prose about the bug."):
        resp = client.post("/api/code/debug", json={"code": "x = 1", "error_message": "e"})

    body = resp.get_json()
    assert body["explanation"] == "Not JSON at all, just prose about the bug."
    assert body["is_suggestion"] is True


# ---------------------------------------------------------------------------
# Review — persists CodeReview + CodeAnalysis
# ---------------------------------------------------------------------------
def test_review_persists_findings_and_scores(client):
    register_and_verify(client, "code11@example.com")
    login_as(client, "code11@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])

    payload = json.dumps({
        "findings": [{"severity": "Medium", "title": "No input validation", "description": "...", "line": 1}],
        "scores": {"quality": 80, "security": 70, "performance": 90, "maintainability": 85},
    })
    with _mock_ai(payload):
        resp = client.post("/api/code/review", json={"file_id": file_["id"]})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["scores"]["quality"] == 80
    assert len(body["findings"]) == 1

    fetched = client.get(f"/api/code/reviews/{body['review_id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["findings"][0]["severity"] == "Medium"


def test_review_falls_back_to_single_finding_on_bad_json(client):
    register_and_verify(client, "code12@example.com")
    login_as(client, "code12@example.com")

    with _mock_ai("This code looks fine overall, no major issues."):
        resp = client.post("/api/code/review", json={"code": "x = 1"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert len(body["findings"]) == 1
    assert body["findings"][0]["severity"] == "Suggestion"


def test_user_b_cannot_fetch_user_a_review(client):
    register_and_verify(client, "code13a@example.com")
    register_and_verify(client, "code13b@example.com")

    login_as(client, "code13a@example.com")
    with _mock_ai(json.dumps({"findings": [], "scores": {}})):
        resp = client.post("/api/code/review", json={"code": "x = 1"})
    review_id = resp.get_json()["review_id"]
    client.post("/api/auth/logout")

    login_as(client, "code13b@example.com")
    fetched = client.get(f"/api/code/reviews/{review_id}")
    assert fetched.status_code == 404


# ---------------------------------------------------------------------------
# Optimize
# ---------------------------------------------------------------------------
def test_optimize_returns_original_and_optimized_side_by_side(client):
    register_and_verify(client, "code14@example.com")
    login_as(client, "code14@example.com")

    payload = json.dumps({"optimized_code": "x = sum(range(10))", "explanation": "used builtin sum"})
    with _mock_ai(payload):
        resp = client.post("/api/code/optimize", json={"code": "x = 0\nfor i in range(10): x += i"})

    body = resp.get_json()
    assert body["original_code"] == "x = 0\nfor i in range(10): x += i"
    assert body["optimized_code"] == "x = sum(range(10))"


# ---------------------------------------------------------------------------
# Tests — persists GeneratedTest
# ---------------------------------------------------------------------------
def test_generate_tests_persists_and_strips_code_fence(client):
    register_and_verify(client, "code15@example.com")
    login_as(client, "code15@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])

    with _mock_ai("```python\ndef test_add():\n    assert add(1, 2) == 3\n```"):
        resp = client.post("/api/code/tests", json={"file_id": file_["id"], "framework": "pytest"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["generated_code"] == "def test_add():\n    assert add(1, 2) == 3"
    assert "```" not in body["generated_code"]


# ---------------------------------------------------------------------------
# Documentation — persists Document
# ---------------------------------------------------------------------------
def test_generate_documentation_persists(client):
    register_and_verify(client, "code16@example.com")
    login_as(client, "code16@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])

    with _mock_ai('"""Adds two numbers."""'):
        resp = client.post("/api/code/documentation", json={"file_id": file_["id"], "doc_type": "docstring"})

    assert resp.status_code == 201
    assert "Adds two numbers" in resp.get_json()["content"]


# ---------------------------------------------------------------------------
# Isolation: can't attach a review/test/doc to a project you don't own
# ---------------------------------------------------------------------------
def test_cannot_attach_review_to_project_you_dont_own(client):
    register_and_verify(client, "code17a@example.com")
    register_and_verify(client, "code17b@example.com")

    login_as(client, "code17a@example.com")
    project = _create_project(client)
    client.post("/api/auth/logout")

    login_as(client, "code17b@example.com")
    with _mock_ai(json.dumps({"findings": [], "scores": {}})):
        resp = client.post("/api/code/review", json={"code": "x = 1", "project_id": project["id"]})
    assert resp.status_code == 404


def test_code_endpoints_require_authentication(client):
    resp = client.post("/api/code/explain", json={"code": "x = 1"})
    assert resp.status_code == 401
