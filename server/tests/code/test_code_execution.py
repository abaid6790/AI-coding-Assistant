"""
Route-level tests for POST /api/code/run. No mocking needed — unlike
the AI endpoints, this genuinely executes short, fast Python snippets
(the same thing Phase 12's tests already proved is safe and quick), so
these tests exercise the real path end to end. The one thing mocked is
the timeout/truncated plumbing (test_run_reflects_timeout_flag) — that
scenario would otherwise cost 10 real seconds per run, unnecessary
here since Phase 12 already proves the timeout mechanism itself works;
this test only needs to prove the ROUTE surfaces that field correctly.
"""
from unittest.mock import patch

from tests.conftest import register_and_verify, login_as
from services.execution.common import ExecutionResult


def _login(client, email="run1@example.com"):
    register_and_verify(client, email)
    login_as(client, email)


def test_run_requires_authentication(client):
    resp = client.post("/api/code/run", json={"language": "python", "code": "print(1)"})
    assert resp.status_code == 401


def test_run_success(client):
    _login(client, "run2@example.com")
    resp = client.post("/api/code/run", json={"language": "python", "code": "print('Hello World')"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["stdout"] == "Hello World\n"
    assert body["exit_code"] == 0
    assert body["stderr"] == ""


def test_run_runtime_error_is_still_a_200(client):
    """The spec's envelope has success: false for a failing run — the
    HTTP layer says the REQUEST worked; the code itself failing is
    data in the body, not an HTTP error status."""
    _login(client, "run3@example.com")
    resp = client.post("/api/code/run", json={"language": "python", "code": "print(undefined_name)"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert body["exit_code"] != 0
    assert "NameError" in body["stderr"]


def test_run_error_is_not_replaced_with_generic_message(client):
    """Explicit spec requirement: don't hide or generalize the real error."""
    _login(client, "run4@example.com")
    resp = client.post("/api/code/run", json={"language": "python", "code": "1 / 0"})
    body = resp.get_json()
    assert "ZeroDivisionError" in body["stderr"]
    assert "Traceback" in body["stderr"]


def test_run_missing_code_is_400(client):
    _login(client, "run5@example.com")
    resp = client.post("/api/code/run", json={"language": "python"})
    assert resp.status_code == 400
    assert resp.get_json()["field_errors"]["code"] == "required"


def test_run_missing_language_is_400(client):
    _login(client, "run6@example.com")
    resp = client.post("/api/code/run", json={"code": "print(1)"})
    assert resp.status_code == 400
    assert resp.get_json()["field_errors"]["language"] == "unsupported"


def test_run_unsupported_language_is_400_with_clear_message(client):
    _login(client, "run7@example.com")
    resp = client.post("/api/code/run", json={"language": "cobol", "code": "print(1)"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["field_errors"]["language"] == "unsupported"
    assert "python" in body["error"].lower()  # tells the caller what IS supported


def test_run_response_includes_all_expected_fields(client):
    _login(client, "run8@example.com")
    resp = client.post("/api/code/run", json={"language": "python", "code": "print(1)"})
    body = resp.get_json()
    for key in ("success", "stdout", "stderr", "exit_code", "timed_out", "truncated"):
        assert key in body
    assert body["timed_out"] is False
    assert body["truncated"] is False


def test_run_reflects_timeout_flag(client):
    """Confirms the route surfaces the timed_out flag correctly, without
    spending 10 real seconds per test run — the timeout mechanism
    itself is already proven at the service layer (Phase 12's tests)."""
    _login(client, "run9@example.com")
    fake_result = ExecutionResult(
        success=False, stdout="", stderr="[Execution timed out after 10 seconds and was terminated.]",
        exit_code=None, timed_out=True, truncated=False,
    )
    with patch("services.code.execution_service.run_code", return_value=fake_result):
        resp = client.post("/api/code/run", json={"language": "python", "code": "while True: pass"})

    body = resp.get_json()
    assert resp.status_code == 200
    assert body["success"] is False
    assert body["timed_out"] is True


def test_run_returns_503_when_server_at_capacity(client):
    """Phase 17: the concurrency cap is a request-level failure (the
    server couldn't even attempt the run), distinct from a code-
    execution outcome — a real 503, not success: false in the envelope."""
    _login(client, "run14@example.com")
    from services.execution.common import ExecutionCapacityError

    with patch("services.code.execution_service.run_code", side_effect=ExecutionCapacityError):
        resp = client.post("/api/code/run", json={"language": "python", "code": "print(1)"})

    assert resp.status_code == 503


def test_run_multiple_times_in_one_session(client):
    """The core interactive loop the spec describes: run, see an error,
    run again after a fix. Nothing should get "stuck" between calls —
    each run uses a fresh temp directory (see Phase 12)."""
    _login(client, "run10@example.com")

    first = client.post("/api/code/run", json={"language": "python", "code": "print(undefined)"})
    assert first.get_json()["success"] is False

    second = client.post("/api/code/run", json={"language": "python", "code": "print('fixed')"})
    assert second.get_json()["success"] is True
    assert second.get_json()["stdout"] == "fixed\n"


# ---------------------------------------------------------------------------
# JavaScript (Phase 16) — confirms the second language is wired through
# the actual route, not just the service layer in isolation
# ---------------------------------------------------------------------------
def test_run_javascript_success(client):
    _login(client, "run11@example.com")
    resp = client.post("/api/code/run", json={"language": "javascript", "code": "console.log('Hello JS');"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["stdout"] == "Hello JS\n"


def test_run_javascript_runtime_error_is_still_a_200(client):
    _login(client, "run12@example.com")
    resp = client.post("/api/code/run", json={"language": "javascript", "code": "console.log(notDefined);"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "ReferenceError" in body["stderr"]


def test_run_language_is_case_insensitive(client):
    """Matches the existing pattern elsewhere in the app (language
    fields are lowercased before comparison) — "Python" and "python"
    should both work rather than surprising a client that sends
    Title Case."""
    _login(client, "run13@example.com")
    resp = client.post("/api/code/run", json={"language": "JavaScript", "code": "console.log(1);"})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
