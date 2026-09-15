import json
from unittest.mock import patch

from tests.conftest import register_and_verify, login_as
from services.ai.base import AIResponse


def _create_project(client, name="P"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["project"]


def _create_file(client, project_id, filename="app.py", content="def add(a, b):\n    return a + b"):
    resp = client.post(f"/api/projects/{project_id}/files", json={"filename": filename, "content": content, "language": "python"})
    assert resp.status_code == 201
    return resp.get_json()["file"]


def _mock_ai(text):
    return patch("services.ai.service.AIService.generate", return_value=AIResponse(text=text, provider="gemini", model="m"))


def _run_review(client, project_id, findings=None, scores=None, complexity="Low complexity."):
    payload = json.dumps({
        "findings": findings if findings is not None else [{"severity": "High", "title": "Bug", "description": "d", "line": 2}],
        "scores": scores if scores is not None else {"quality": 75, "security": 60, "performance": 90, "maintainability": 80},
        "complexity": complexity,
    })
    with _mock_ai(payload):
        return client.post("/api/code/review", json={"project_id": project_id, "code": "x = 1"})


# ---------------------------------------------------------------------------
# Reviews list
# ---------------------------------------------------------------------------
def test_list_project_reviews(client):
    register_and_verify(client, "p9a@example.com")
    login_as(client, "p9a@example.com")
    project = _create_project(client)
    _run_review(client, project["id"])

    resp = client.get(f"/api/projects/{project['id']}/reviews")
    assert resp.status_code == 200
    reviews = resp.get_json()["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["findings"][0]["severity"] == "High"


def test_user_b_cannot_list_user_a_project_reviews(client):
    register_and_verify(client, "p9b@example.com")
    register_and_verify(client, "p9c@example.com")

    login_as(client, "p9b@example.com")
    project = _create_project(client)
    _run_review(client, project["id"])
    client.post("/api/auth/logout")

    login_as(client, "p9c@example.com")
    resp = client.get(f"/api/projects/{project['id']}/reviews")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests / documents lists
# ---------------------------------------------------------------------------
def test_list_and_get_project_test(client):
    register_and_verify(client, "p9d@example.com")
    login_as(client, "p9d@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])

    with _mock_ai("```python\ndef test_add():\n    assert add(1, 2) == 3\n```"):
        created = client.post("/api/code/tests", json={"file_id": file_["id"], "framework": "pytest"})
    test_id = created.get_json()["test_id"]

    listed = client.get(f"/api/projects/{project['id']}/tests")
    assert listed.status_code == 200
    assert len(listed.get_json()["tests"]) == 1
    assert "generated_code" not in listed.get_json()["tests"][0]  # list view omits full code

    fetched = client.get(f"/api/projects/{project['id']}/tests/{test_id}")
    assert fetched.status_code == 200
    assert "assert add(1, 2) == 3" in fetched.get_json()["test"]["generated_code"]


def test_list_and_get_project_document(client):
    register_and_verify(client, "p9e@example.com")
    login_as(client, "p9e@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])

    with _mock_ai('"""Adds two numbers."""'):
        created = client.post("/api/code/documentation", json={"file_id": file_["id"], "doc_type": "docstring"})
    doc_id = created.get_json()["document_id"]

    listed = client.get(f"/api/projects/{project['id']}/documents")
    assert listed.status_code == 200
    assert "content" not in listed.get_json()["documents"][0]

    fetched = client.get(f"/api/projects/{project['id']}/documents/{doc_id}")
    assert "Adds two numbers" in fetched.get_json()["document"]["content"]


def test_user_b_cannot_fetch_user_a_test_via_their_own_project(client):
    """Same two-step ownership check as project files: a test id valid
    for the caller's own project shouldn't resolve if it actually
    belongs to someone else's test row."""
    register_and_verify(client, "p9f@example.com")
    register_and_verify(client, "p9g@example.com")

    login_as(client, "p9f@example.com")
    project_a = _create_project(client)
    file_a = _create_file(client, project_a["id"])
    with _mock_ai("```python\nassert True\n```"):
        created = client.post("/api/code/tests", json={"file_id": file_a["id"]})
    test_id = created.get_json()["test_id"]
    client.post("/api/auth/logout")

    login_as(client, "p9g@example.com")
    project_b = _create_project(client, "B")
    resp = client.get(f"/api/projects/{project_b['id']}/tests/{test_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analysis dashboard
# ---------------------------------------------------------------------------
def test_analysis_dashboard_with_no_reviews_yet(client):
    register_and_verify(client, "p9h@example.com")
    login_as(client, "p9h@example.com")
    project = _create_project(client)

    resp = client.get(f"/api/projects/{project['id']}/analysis")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["latest"] is None
    assert body["issues_found"] == 0
    assert body["reviews_count"] == 0


def test_analysis_dashboard_reflects_latest_review(client):
    register_and_verify(client, "p9i@example.com")
    login_as(client, "p9i@example.com")
    project = _create_project(client)

    _run_review(client, project["id"], findings=[
        {"severity": "Critical", "title": "SQL injection", "description": "d", "line": 5},
        {"severity": "Low", "title": "Naming", "description": "d", "line": 10},
    ], scores={"quality": 60, "security": 30, "performance": 70, "maintainability": 65})

    resp = client.get(f"/api/projects/{project['id']}/analysis")
    body = resp.get_json()
    assert body["latest"]["quality_score"] == 60
    assert body["latest"]["complexity_summary"] == "Low complexity."
    assert body["issues_found"] == 2
    assert body["issues_by_severity"] == {"Critical": 1, "Low": 1}
    assert body["reviews_count"] == 1


def test_analysis_dashboard_history_is_chronological(client):
    register_and_verify(client, "p9j@example.com")
    login_as(client, "p9j@example.com")
    project = _create_project(client)

    _run_review(client, project["id"], scores={"quality": 50})
    _run_review(client, project["id"], scores={"quality": 90})

    resp = client.get(f"/api/projects/{project['id']}/analysis")
    history = resp.get_json()["history"]
    assert len(history) == 2
    assert [h["quality_score"] for h in history] == [50, 90]  # oldest first
    assert resp.get_json()["latest"]["quality_score"] == 90


def test_user_b_cannot_view_user_a_project_analysis(client):
    register_and_verify(client, "p9k@example.com")
    register_and_verify(client, "p9l@example.com")

    login_as(client, "p9k@example.com")
    project = _create_project(client)
    _run_review(client, project["id"])
    client.post("/api/auth/logout")

    login_as(client, "p9l@example.com")
    resp = client.get(f"/api/projects/{project['id']}/analysis")
    assert resp.status_code == 404
