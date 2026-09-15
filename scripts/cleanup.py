#!/usr/bin/env python3
"""
Resets local dev artifacts: __pycache__/.pytest_cache directories and
the Vite build output, always. The local SQLite database and
node_modules are only removed if explicitly requested, since those are
expensive to regenerate and shouldn't disappear by accident. Never
touches .env or anything actually placed under data/uploads or
data/projects.

Usage:
    python scripts/cleanup.py                # caches + build output only
    python scripts/cleanup.py --db           # also drop the local database
    python scripts/cleanup.py --node-modules # also remove node_modules/
"""
import argparse
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def remove(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Removed {path}")
    elif os.path.isfile(path):
        os.remove(path)
        print(f"Removed {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", action="store_true", help="Also delete the local SQLite database.")
    parser.add_argument("--node-modules", action="store_true", help="Also remove node_modules/.")
    args = parser.parse_args()

    for root, dirs, _files in os.walk(PROJECT_ROOT):
        if "node_modules" in dirs and not args.node_modules:
            dirs.remove("node_modules")  # don't descend into it unless we're removing it
        for name in ("__pycache__", ".pytest_cache"):
            if name in dirs:
                remove(os.path.join(root, name))
                dirs.remove(name)

    remove(os.path.join(PROJECT_ROOT, "dist"))

    if args.db:
        remove(os.path.join(PROJECT_ROOT, "data", "database", "app.db"))

    if args.node_modules:
        remove(os.path.join(PROJECT_ROOT, "node_modules"))

    print("Cleanup complete.")


if __name__ == "__main__":
    main()
