#!/usr/bin/env python3
"""
One-time local setup: creates the project-level .env from .env.example
if it doesn't exist yet, and makes sure the data/ directories exist.

Deliberately does NOT install Python/Node dependencies — that stays an
explicit, visible step (`pip install -r server/requirements.txt`,
`npm install`) rather than something this script does silently on your
behalf.

Usage:
    python scripts/setup.py
"""
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)


def main():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    example_path = os.path.join(PROJECT_ROOT, ".env.example")

    if os.path.exists(env_path):
        print(".env already exists — leaving it alone.")
    else:
        shutil.copyfile(example_path, env_path)
        print("Created .env from .env.example — edit it before running the app.")

    for sub in ("database", "uploads", "projects"):
        path = os.path.join(PROJECT_ROOT, "data", sub)
        os.makedirs(path, exist_ok=True)
    print("data/ directories ready.")

    print("\nNext steps:")
    print("  pip install -r server/requirements.txt")
    print("  python app.py     # builds the frontend automatically, then runs everything")


if __name__ == "__main__":
    main()
