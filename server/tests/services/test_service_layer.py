"""
Everything else in the suite tests through the Flask test client (HTTP
in, HTTP out). These tests call service functions directly — no
request/response cycle — which is exactly the payoff of having pulled
business logic out of the route handlers in Phase "restructure": the
logic is now testable as plain Python, not just as an HTTP contract.
"""
from services.code.common import resolve_source
from services.projects.project_service import _get_owned_file_in_project


def test_resolve_source_rejects_empty_code(app):
    with app.test_request_context():
        result, err = resolve_source({})
        assert result is None
        assert err[1] == 400


def test_resolve_source_accepts_direct_code(app):
    with app.test_request_context():
        result, err = resolve_source({"code": "x = 1", "language": "python"})
        assert err is None
        code, language, file_, project_id = result
        assert code == "x = 1"
        assert language == "python"
        assert file_ is None
        assert project_id is None


def test_get_owned_file_in_project_is_a_real_function():
    # Smoke test confirming the helper survived the extraction from
    # api/projects.py into the service module with its name intact —
    # a refactor that silently dropped or renamed it would break this
    # import at collection time, before this assertion even runs.
    assert callable(_get_owned_file_in_project)
