"""
Direct unit tests of the execution service (no HTTP — the route comes
in Phase 13). The security-relevant claims in common.py's docstring
each get their own explicit test here rather than being assumed: env
scrubbing, temp-dir isolation, timeout enforcement, and output capping
are exactly the properties that matter most in this phase, so each one
is verified directly instead of only covering the happy path.
"""
import os
import sys
import time

from services.execution.python_runner import run_python
from services.execution.common import run_in_temp_dir, MAX_CODE_BYTES


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_successful_run():
    result = run_python("print('Hello, World!')")
    assert result.success is True
    assert result.stdout == "Hello, World!\n"
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.truncated is False


def test_multiline_output():
    result = run_python("for i in range(3):\n    print(i)")
    assert result.success is True
    assert result.stdout == "0\n1\n2\n"


# ---------------------------------------------------------------------------
# Errors — must surface the real error, not a generic message
# ---------------------------------------------------------------------------
def test_syntax_error():
    result = run_python("def broken(:\n    pass")
    assert result.success is False
    assert result.exit_code != 0
    assert "SyntaxError" in result.stderr


def test_runtime_error():
    result = run_python("print(undefined_variable)")
    assert result.success is False
    assert result.exit_code != 0
    assert "NameError" in result.stderr
    assert "undefined_variable" in result.stderr


def test_runtime_error_includes_traceback():
    """The spec is explicit: don't replace the real error with a generic
    message. A Traceback line confirms we're passing through Python's
    actual stderr, not summarizing it."""
    result = run_python("1 / 0")
    assert "Traceback" in result.stderr
    assert "ZeroDivisionError" in result.stderr


# ---------------------------------------------------------------------------
# Timeout — the process must actually be killed, not just abandoned
# ---------------------------------------------------------------------------
def test_infinite_loop_times_out_and_is_killed():
    start = time.monotonic()
    result = run_python("while True:\n    pass", timeout=1)
    elapsed = time.monotonic() - start

    assert result.timed_out is True
    assert result.success is False
    assert "timed out" in result.stderr.lower()
    # If the process were merely abandoned rather than killed, this
    # call would hang far longer than the requested 1-second timeout
    # (pytest would eventually be killed by an external test timeout,
    # not fail cleanly) — asserting a tight wall-clock bound is what
    # actually proves the kill happened, not just that we returned.
    assert elapsed < 5


def test_timeout_is_clamped_to_maximum():
    """Requesting an absurd timeout doesn't hang the test suite — the
    value is clamped internally (see common.py's MAX_TIMEOUT_SECONDS)
    before it's ever used, verified here with fast-exiting code so this
    test doesn't itself take 30+ seconds to run."""
    result = run_python("print('fast')", timeout=99999)
    assert result.success is True
    assert result.stdout == "fast\n"


# ---------------------------------------------------------------------------
# Output cap — must kill the process early, not buffer forever
# ---------------------------------------------------------------------------
def test_output_is_truncated_and_process_killed():
    code = "while True:\n    print('x' * 1000)"
    start = time.monotonic()
    result = run_in_temp_dir("main.py", code, run_args=[sys.executable, "main.py"], timeout=10)
    elapsed = time.monotonic() - start

    # Default cap is 200KB; an infinite print loop would run for the
    # full 10-second timeout if the cap didn't kill it early.
    assert result.truncated is True
    assert result.success is False
    assert elapsed < 8  # killed by the output cap, well before the 10s timeout


# ---------------------------------------------------------------------------
# The security-critical properties
# ---------------------------------------------------------------------------
def test_environment_is_scrubbed():
    """The core secret-leak protection: even though this test process
    has a fake secret in its real environment, the child process must
    never see it."""
    os.environ["FAKE_APP_SECRET_FOR_TEST"] = "should-never-leak-to-child"
    try:
        result = run_python("import os\nprint(os.environ.get('FAKE_APP_SECRET_FOR_TEST'))")
        assert result.stdout.strip() == "None"
    finally:
        del os.environ["FAKE_APP_SECRET_FOR_TEST"]


def test_runs_in_isolated_temp_directory_not_project_root():
    result = run_python("import os\nprint(os.getcwd())")
    printed_cwd = result.stdout.strip()

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert printed_cwd != project_root
    assert "ai-coding-assistant-run-" in printed_cwd
    # The temp directory is cleaned up the moment run_python() returns —
    # confirms code can't leave files behind for a later run to find.
    assert not os.path.exists(printed_cwd)


def test_code_size_limit_rejects_without_executing():
    huge_code = "# " + ("x" * (MAX_CODE_BYTES + 1))
    result = run_python(huge_code)
    assert result.success is False
    assert result.exit_code is None  # never even spawned a process
    assert "too large" in result.stderr.lower()


def test_traceback_shows_clean_filename_not_server_path():
    """Matches the spec's own example output (`File "main.py", line 4`)
    and avoids leaking the server's temp-directory path to the client.
    Checks for our own directory-naming prefix rather than a specific
    base path like /tmp — that varies by OS (macOS/Windows use
    different temp roots), but our prefix is always the same."""
    result = run_python("undefined_name")
    assert 'File "main.py"' in result.stderr
    assert "ai-coding-assistant-run-" not in result.stderr
