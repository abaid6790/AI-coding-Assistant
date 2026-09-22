"""
Phase 17 hardening tests. Each targets one specific gap that was
explicitly documented (not silently ignored) after Phase 12: the
direct-child-only kill on timeout, no memory ceiling, and no
concurrency bound. Process-tree killing and the memory limit are
POSIX-only (see common.py's docstrings for why), so those two are
skipped on Windows rather than asserted against behavior that
genuinely doesn't apply there.
"""
import os
import threading
import time

import pytest

from services.execution.python_runner import run_python
from services.execution.common import ExecutionCapacityError
import services.execution.common as common_module


def _pid_alive(pid: int) -> bool:
    """True only if the process is genuinely still running — not just
    present in the process table. A killed process becomes a zombie
    (state Z) until its parent (or, once orphaned, an init/subreaper)
    reaps it; os.kill(pid, 0) alone reports a zombie as "existing",
    which would make a correctly-killed process look alive if the
    parent that's supposed to reap it is itself dead and no subreaper
    picks it up promptly (true of minimal containers without an init
    like tini — exactly the environment these tests may run in). A
    zombie is definitionally already dead: it's not running, using
    CPU, or holding resources — it's just an unreaped exit-status
    entry, so it must be treated as dead for what this test actually
    verifies (did we terminate the process, not has some init cleaned
    up its table entry yet)."""
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("State:"):
                    return "Z" not in line  # "Z (zombie)" => already dead
        return True  # /proc/<pid>/status existed but had no State line — treat as alive, unexpected
    except FileNotFoundError:
        return False  # fully reaped already
    except PermissionError:
        return True  # exists and we can't inspect it — still alive for our purposes


# ---------------------------------------------------------------------------
# Process-tree kill (closes the Phase 12-documented gap: only the direct
# child was killed on timeout, not anything it spawned itself)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not os.path.isdir("/proc"), reason="Verifies the POSIX process-group kill path via /proc (Linux-specific)")
def test_grandchild_process_is_killed_on_timeout(tmp_path):
    pid_file = tmp_path / "grandchild_pid.txt"
    code = f"""
import subprocess, sys, time
p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
with open(r"{pid_file}", "w") as f:
    f.write(str(p.pid))
    f.flush()
time.sleep(30)
"""
    result = run_python(code, timeout=1)
    assert result.timed_out is True

    time.sleep(0.3)  # brief grace period for the OS to finish tearing the tree down
    grandchild_pid = int(pid_file.read_text().strip())
    assert not _pid_alive(grandchild_pid), (
        "the grandchild process outlived the timed-out parent — "
        "process-TREE killing isn't actually killing the tree"
    )


# ---------------------------------------------------------------------------
# Memory limit (POSIX only — see node_runner.py for why this is NOT
# applied to JavaScript)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(os.name == "nt", reason="RLIMIT_AS is POSIX-only")
def test_memory_bomb_hits_the_memory_ceiling():
    code = "data = []\nwhile True:\n    data.append('x' * 10_000_000)"
    result = run_python(code, timeout=10)
    assert result.success is False
    assert "MemoryError" in result.stderr
    # Confirms the ceiling caught it well before the wall-clock timeout
    # would have — a genuinely different failure mode than a timeout.
    assert result.timed_out is False


# ---------------------------------------------------------------------------
# Concurrency cap
# ---------------------------------------------------------------------------
def test_concurrency_cap_rejects_when_at_capacity():
    original_semaphore = common_module._execution_semaphore
    common_module._execution_semaphore = threading.Semaphore(1)
    try:
        results = []

        def slow_run():
            results.append(run_python("import time\ntime.sleep(0.8)"))

        t = threading.Thread(target=slow_run)
        t.start()
        time.sleep(0.2)  # let the first run actually acquire the semaphore

        with pytest.raises(ExecutionCapacityError):
            run_python("print('should be rejected')")

        t.join(timeout=5)
        assert len(results) == 1
        assert results[0].success is True
    finally:
        common_module._execution_semaphore = original_semaphore


def test_concurrency_slot_is_released_after_a_run_completes():
    """The cap must free up again once a run finishes — otherwise every
    execution would permanently consume a slot and the server would
    eventually refuse all runs forever."""
    original_semaphore = common_module._execution_semaphore
    common_module._execution_semaphore = threading.Semaphore(1)
    try:
        first = run_python("print('first')")
        assert first.success is True
        # The semaphore slot from the first run should be back to 1
        # (fully released) — a second run right after must succeed too.
        second = run_python("print('second')")
        assert second.success is True
    finally:
        common_module._execution_semaphore = original_semaphore
