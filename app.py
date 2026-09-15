#!/usr/bin/env python3
"""
Run the WHOLE application — frontend and backend, one process, one
port — with a single command from the project root:

    python app.py

No `cd server`, no separate `npm run dev`. On first run (no built
frontend yet), this script builds it automatically (`npm install` +
`npm run build`) before starting the server, so a completely fresh
clone still only needs this one command — as long as Python
dependencies are already installed (`pip install -r server/requirements.txt`)
and Node.js/npm are available on your PATH for the one-time build.

What this actually does: ensures the frontend is built, then imports
and runs the real Flask app defined in server/app.py — that file's
`_register_frontend()` is what serves the built frontend for every
non-/api/* route, so the frontend and API genuinely share one process.

Active frontend development (hot reload on every save) is a different
workflow — see "Developing with hot reload" in README.md — but for
just running the application, this is the one command you need.
"""
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DIST_INDEX = os.path.join(DIST_DIR, "index.html")
NODE_MODULES = os.path.join(PROJECT_ROOT, "node_modules")

# On Windows, npm/node are installed as npm.cmd/node.cmd — batch-file
# shims that subprocess.run() cannot execute directly when shell=False
# (Windows' CreateProcess needs cmd.exe to interpret a .cmd file; macOS/
# Linux have no such distinction, npm there is a real executable). The
# command list is entirely hardcoded below (no user input reaches it),
# so shell=True on Windows carries no injection risk.
_USE_SHELL = os.name == "nt"


def _run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, shell=_USE_SHELL)
    except FileNotFoundError:
        print(
            f"\nCould not run '{cmd[0]}'. This usually means Node.js isn't "
            "installed, or your terminal's PATH doesn't include it yet.\n\n"
            "1. Install Node.js from https://nodejs.org (npm comes with it).\n"
            "2. Close and reopen your terminal (PATH changes need a fresh "
            "shell to take effect) — a fresh venv activation isn't enough.\n"
            f"3. Confirm it worked by running: {'npm --version' if _USE_SHELL else cmd[0] + ' --version'}\n"
            "4. Run `python app.py` again."
        )
        sys.exit(1)
    if result.returncode != 0:
        print(f"\n'{' '.join(cmd)}' failed (exit code {result.returncode}). "
              "Fix the error above and run `python app.py` again.")
        sys.exit(result.returncode)


def ensure_frontend_built() -> None:
    if os.path.isfile(DIST_INDEX):
        return  # already built — nothing to do

    print("No built frontend found — building it now (this only happens once).\n")

    if not os.path.isdir(NODE_MODULES):
        print("Installing frontend dependencies...")
        _run(["npm", "install"])

    print("\nBuilding the frontend (npm run build)...")
    _run(["npm", "run", "build"])
    print("\nFrontend build complete.\n")


def ensure_backend_deps_available() -> None:
    """A clear error beats an ImportError traceback for the most common
    first-run mistake: forgetting `pip install -r server/requirements.txt`."""
    try:
        import flask  # noqa: F401
    except ImportError:
        print(
            "Python dependencies aren't installed yet. Run this once:\n\n"
            "    pip install -r server/requirements.txt\n\n"
            "then run `python app.py` again."
        )
        sys.exit(1)


def main() -> None:
    ensure_backend_deps_available()
    ensure_frontend_built()

    sys.path.insert(0, SERVER_DIR)
    from app import app  # noqa: E402  (server/app.py's Flask instance)

    port = int(os.environ.get("PORT", 5000))
    print(f"AI Coding Assistant running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))


if __name__ == "__main__":
    main()
