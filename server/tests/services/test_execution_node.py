"""
JavaScript-specific tests. Env scrubbing, temp-dir isolation, timeout
enforcement, and output capping are all shared machinery (services/
execution/common.py) already proven by test_execution.py's Python
tests — re-testing the same mechanism through a second language would
just be duplication. What's actually new here: Node's error format
differs from Python's, and node_runner.py has its own "Node isn't
available" fallback path that python_runner.py doesn't need.
"""
from unittest.mock import patch

from services.execution.node_runner import run_javascript


def test_successful_run():
    result = run_javascript("console.log('Hello from Node');")
    assert result.success is True
    assert result.stdout == "Hello from Node\n"
    assert result.exit_code == 0


def test_syntax_error():
    result = run_javascript("function broken( {")
    assert result.success is False
    assert result.exit_code != 0
    assert "SyntaxError" in result.stderr


def test_runtime_error():
    result = run_javascript("console.log(undefinedVariable);")
    assert result.success is False
    assert result.exit_code != 0
    assert "ReferenceError" in result.stderr
    assert "undefinedVariable" in result.stderr


def test_node_not_found_gives_clear_error_not_a_crash():
    with patch("services.execution.node_runner.shutil.which", return_value=None):
        result = run_javascript("console.log('should not run');")
    assert result.success is False
    assert result.exit_code is None  # never spawned a process
    assert "not available" in result.stderr.lower()
