"""
Shared execution primitives, language-agnostic — python_runner.py and
node_runner.py both build on run_subprocess()/run_in_temp_dir() rather
than each reimplementing process spawning, timeout handling, and
output capping.

This is a DEVELOPMENT-STAGE execution mechanism: real OS process
isolation, not container/VM-level sandboxing. See SECURITY.md for what
that distinction means in practice. What IS covered, as of Phase 17:

  - Code never runs via exec()/eval() inside the Flask request process
    — always a separate OS process.
  - The child process gets a minimal, scrubbed environment — the app's
    real secrets are never passed through. See _minimal_env().
  - Code runs from a fresh temporary directory, deleted immediately
    after the run. See run_in_temp_dir().
  - A wall-clock timeout forcibly kills the process. See the poll loop
    in run_subprocess().
  - An output-size cap kills the process early rather than letting a
    print loop exhaust server memory. See _drain().
  - On timeout or the output cap, the ENTIRE process tree is killed —
    not just the direct child — so code that spawns its own child
    processes can't outlive the run. See _kill_process_tree().
  - On POSIX, a memory ceiling (RLIMIT_AS) and a CPU-time ceiling
    (RLIMIT_CPU) are set on the child before it starts running user
    code at all, as a backstop behind the wall-clock timeout — see
    _build_run_args() and the module docstring note on why this uses
    an exec-wrapper rather than Popen's preexec_fn.
  - A concurrency cap bounds how many executions can run at once in
    this process, so one user (or several) can't exhaust the server by
    launching unlimited simultaneous runs. See ExecutionCapacityError
    and its caveat about being per-process, not global.

What is still NOT covered, honestly: no network isolation (executed
code can make outbound network requests — this needs a real
container/VM to fix properly, not a partial in-process measure that
would just create false confidence), no filesystem access restriction
beyond "runs in an empty temp directory" (the code can still read any
path the server process has OS permission to read), and the memory/CPU
ceilings only apply on POSIX — Windows has no stdlib equivalent
(reaching for that would mean either a new dependency or reimplementing
Job Objects by hand, both deferred). See SECURITY.md's "Known gaps".
"""
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass

try:
    import resource  # POSIX only
    _HAS_RESOURCE_MODULE = True
except ImportError:
    _HAS_RESOURCE_MODULE = False

DEFAULT_TIMEOUT_SECONDS = 10
MAX_TIMEOUT_SECONDS = 30
MAX_OUTPUT_BYTES = 200_000  # per stream (stdout/stderr) — enough for a real debug session, not enough to OOM the server
MAX_CODE_BYTES = 1 * 1024 * 1024  # matches the file-size cap used elsewhere in the app (see ProjectFile validation)
MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256 MB address-space ceiling per execution (POSIX only)
MAX_CONCURRENT_EXECUTIONS = 5


class ExecutionCapacityError(Exception):
    """Raised when this process is already running MAX_CONCURRENT_EXECUTIONS
    at once. This is an in-process semaphore — it bounds concurrency
    within a single worker process, not globally across a multi-worker
    deployment (multiple gunicorn workers each get their own cap). A
    true global cap needs a shared backend (Redis or similar), the
    same caveat the existing rate limiter already has — see
    SECURITY.md."""


_execution_semaphore = threading.Semaphore(MAX_CONCURRENT_EXECUTIONS)


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool = False
    truncated: bool = False


def _minimal_env() -> dict:
    """Only what the interpreter/runtime itself needs to start — nothing
    from this process's real environment variables is passed through.
    This is the actual secret-leak protection: it doesn't matter how
    carefully prompts or file access are restricted elsewhere if the
    child process could just read os.environ and print the app's
    SECRET_KEY or a Gemini API key."""
    env = {}
    for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME"):
        val = os.environ.get(key)
        if val:
            env[key] = val
    return env


def _build_run_args(args: list[str], timeout: int, apply_memory_limit: bool) -> list[str]:
    """On POSIX, wraps `args` in a small Python bootstrap that sets
    resource limits on ITSELF, then execs into the real command —
    rather than using subprocess.Popen's preexec_fn, which Python's own
    docs warn is unsafe in a multi-threaded parent process (real risk
    here: this Flask app is multi-threaded, and run_subprocess() itself
    spawns drain threads around this same call). Running the limit-
    setting code as the child's own top-level program, before it execs
    into the target, avoids that fork-safety hazard entirely — rlimits
    are inherited across exec() by POSIX design, so the target process
    ends up with the same limits as if preexec_fn had set them, just
    without the deadlock risk.

    apply_memory_limit is per-call, not a global constant, because
    RLIMIT_AS (address-space size) is NOT safe to apply uniformly
    across runtimes: Node's V8 engine reserves a large chunk of virtual
    address space upfront for its heap/CodeRange before running any
    user code at all — this is normal V8 behavior, unrelated to actual
    memory used — and a 256MB ceiling makes V8 itself fail to
    initialize ("Fatal process out of memory") before the executed code
    ever runs. Discovered by this phase's own tests failing on every
    JavaScript run, not assumed safe from documentation. python_runner.py
    passes True; node_runner.py passes False and relies on the wall-
    clock timeout and output cap alone — see node_runner.py's docstring.

    The CPU-time ceiling (RLIMIT_CPU) doesn't have this problem — it's
    always applied when supported. It's the per-call timeout plus a
    small grace margin, not the global MAX_TIMEOUT_SECONDS — a backstop
    behind the wall-clock kill in run_subprocess()'s poll loop, meant
    to fire only if that primary mechanism somehow didn't.
    """
    if os.name == "nt" or not _HAS_RESOURCE_MODULE:
        return args

    cpu_seconds = timeout + 2
    limit_statements = f"resource.setrlimit(resource.RLIMIT_CPU, ({cpu_seconds}, {cpu_seconds}));"
    if apply_memory_limit:
        limit_statements = (
            f"resource.setrlimit(resource.RLIMIT_AS, ({MAX_MEMORY_BYTES}, {MAX_MEMORY_BYTES}));"
            + limit_statements
        )
    bootstrap = f"import resource, os, sys;{limit_statements}os.execvp(sys.argv[1], sys.argv[1:])"
    return [sys.executable, "-c", bootstrap] + args


def _kill_process_tree(process: subprocess.Popen) -> None:
    """Kills the process AND any children it spawned itself, not just
    the direct child — requires the process to have been started with
    start_new_session=True (POSIX) or CREATE_NEW_PROCESS_GROUP
    (Windows), both set in run_subprocess()'s Popen call."""
    if os.name == "nt":
        # taskkill /T recurses through the whole process tree — this is
        # the reliable way to do this on Windows; sending
        # CTRL_BREAK_EVENT only works for processes that handle the
        # console event, which arbitrary executed code won't.
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True, timeout=5,
            )
        except Exception:
            process.kill()  # best-effort fallback if taskkill itself fails
    else:
        try:
            os.killpg(os.getpgid(process.pid), 9)  # SIGKILL the whole process group
        except ProcessLookupError:
            pass  # already dead
        except Exception:
            process.kill()


def _drain(stream, sink: list, stop_event: threading.Event, max_bytes: int) -> None:
    """Reads a stream in fixed-size chunks (NOT readline()) so the byte
    cap is accurate even for output with no newlines — a `while True:
    print(x, end="")` loop would otherwise never trip a newline-based
    cap, since readline() blocks until it sees one."""
    total = 0
    try:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            sink.append(chunk)
            total += len(chunk.encode("utf-8", errors="replace"))
            if total >= max_bytes:
                stop_event.set()
                break
    finally:
        stream.close()


def run_subprocess(
    args: list[str],
    cwd: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
    apply_memory_limit: bool = True,
) -> ExecutionResult:
    """Runs `args` as a subprocess in `cwd` with a scrubbed environment,
    a wall-clock timeout, an output-size cap, and (POSIX) a CPU-time
    ceiling always, plus a memory ceiling when apply_memory_limit is
    True (see _build_run_args()'s docstring for why that one is
    per-call, not universal). Timeout and the output cap both result in
    the WHOLE process tree being killed, not just the call returning
    early while something keeps running — an abandoned-but-still-
    running process (or one of its children) is exactly the resource
    leak a timeout is supposed to prevent."""
    timeout = max(1, min(timeout, MAX_TIMEOUT_SECONDS))

    popen_kwargs = dict(
        args=_build_run_args(args, timeout, apply_memory_limit),
        cwd=cwd,
        env=_minimal_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True  # own process group, so _kill_process_tree can kill it whole

    process = subprocess.Popen(**popen_kwargs)

    stdout_chunks: list = []
    stderr_chunks: list = []
    stop_event = threading.Event()

    stdout_thread = threading.Thread(
        target=_drain, args=(process.stdout, stdout_chunks, stop_event, max_output_bytes)
    )
    stderr_thread = threading.Thread(
        target=_drain, args=(process.stderr, stderr_chunks, stop_event, max_output_bytes)
    )
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    truncated = False
    start = time.monotonic()

    while True:
        # stop_event is checked FIRST, before poll(): closing a stream
        # in _drain() when the output cap trips can itself cause the
        # child to crash (BrokenPipeError, mid-write) before the next
        # tick of this loop — checking poll() first would misattribute
        # that self-inflicted exit as a normal one and silently lose
        # the truncated flag.
        if stop_event.is_set():
            truncated = True
            _kill_process_tree(process)
            break
        if process.poll() is not None:
            break
        if time.monotonic() - start >= timeout:
            timed_out = True
            _kill_process_tree(process)
            break
        time.sleep(0.05)

    process.wait()  # reap it now that it's finished or been killed
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)

    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)

    if timed_out:
        stderr += f"\n[Execution timed out after {timeout} seconds and was terminated.]"
    if truncated:
        stderr += f"\n[Output truncated — exceeded the {max_output_bytes // 1000} KB limit per stream.]"

    exit_code = process.returncode
    success = exit_code == 0 and not timed_out and not truncated

    return ExecutionResult(
        success=success, stdout=stdout, stderr=stderr, exit_code=exit_code,
        timed_out=timed_out, truncated=truncated,
    )


def run_in_temp_dir(
    filename: str,
    code: str,
    run_args: list[str],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    apply_memory_limit: bool = True,
) -> ExecutionResult:
    """Writes `code` to `filename` in a fresh temporary directory, then
    runs `run_args` (a command whose last element is typically that
    filename) with that directory as cwd. The directory — and the code
    written into it — is deleted the moment this function returns,
    success or failure; it never touches the project's own files.

    apply_memory_limit: pass False for runtimes that reserve large
    virtual address space upfront (Node/V8 — see _build_run_args()'s
    docstring); True (the default) is correct for Python.

    Raises ExecutionCapacityError (see that class's docstring) if this
    process is already running the maximum number of concurrent
    executions — callers should treat that as a request-level failure
    (503-ish "try again"), not a code-execution outcome.
    """
    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return ExecutionResult(
            success=False, stdout="", stderr="Code is too large to execute (max 1 MB).", exit_code=None,
        )

    if not _execution_semaphore.acquire(blocking=False):
        raise ExecutionCapacityError()

    try:
        with tempfile.TemporaryDirectory(prefix="ai-coding-assistant-run-") as run_dir:
            script_path = os.path.join(run_dir, filename)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)
            result = run_subprocess(run_args, cwd=run_dir, timeout=timeout, apply_memory_limit=apply_memory_limit)

            # Tracebacks reference the script by its absolute path
            # (`/tmp/ai-coding-assistant-run-xyz/main.py`) — strip the
            # directory portion so the user sees the clean `main.py`
            # the spec's own example output shows, and so a server-side
            # filesystem path never reaches the client.
            prefix = run_dir + os.sep
            result.stdout = result.stdout.replace(prefix, "")
            result.stderr = result.stderr.replace(prefix, "")
            return result
    finally:
        _execution_semaphore.release()
