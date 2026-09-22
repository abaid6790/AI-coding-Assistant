"""
JavaScript execution via Node — added on top of the exact same shared
primitives python_runner.py uses (services/execution/common.py). Node
is already a hard dependency of this project (the frontend build
needs it), so this adds zero new external requirements.

Same safety model as Python execution — see common.py's module
docstring for the full list of what is and isn't covered — with ONE
deliberate difference: apply_memory_limit=False. Node's V8 engine
reserves a large chunk of virtual address space upfront for its heap/
CodeRange before running any user code at all (normal V8 behavior,
unrelated to actual memory used), and Python's RLIMIT_AS ceiling
(sized for Python's much smaller footprint) makes V8 itself fail to
initialize — this was caught by this phase's own tests failing on
every JavaScript run, not assumed from documentation. JavaScript
execution relies on the wall-clock timeout, the CPU-time ceiling
(unaffected by this), and the output cap alone for now — see
common.py's _build_run_args() docstring for the full explanation.
"""
import shutil

from services.execution.common import ExecutionResult, run_in_temp_dir, DEFAULT_TIMEOUT_SECONDS


def run_javascript(code: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> ExecutionResult:
    node_path = shutil.which("node")
    if node_path is None:
        # Node not being on PATH is an environment problem, not a
        # problem with the user's code — same distinction the route
        # layer draws between a bad request and a failed run, except
        # this one only surfaces if someone deploys without Node
        # available at all (unlikely, since the frontend build needs
        # it too, but worth a clear message over a raw FileNotFoundError).
        return ExecutionResult(
            success=False, stdout="", stderr="Node.js is not available on the server — JavaScript execution is not configured.",
            exit_code=None,
        )

    return run_in_temp_dir(
        filename="main.js",
        code=code,
        run_args=[node_path, "main.js"],
        timeout=timeout,
        apply_memory_limit=False,
    )
