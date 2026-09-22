"""
Python execution — the MVP language for the Run Code feature. See
services/execution/common.py's module docstring for the full safety
model (separate process, scrubbed environment, timeout, output cap).

Uses sys.executable (the interpreter running the Flask app itself)
rather than assuming a "python3" on PATH — this matters on Windows,
where "python3" often doesn't exist even when Python is installed, and
guarantees the same Python version/environment the app itself was
installed with.
"""
import sys

from services.execution.common import ExecutionResult, run_in_temp_dir, DEFAULT_TIMEOUT_SECONDS


def run_python(code: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ExecutionResult:
    return run_in_temp_dir(
        filename="main.py",
        code=code,
        run_args=[sys.executable, "main.py"],
        timeout=timeout,
    )
