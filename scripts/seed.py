#!/usr/bin/env python3
"""
Seeds the local database with a demo user, project, and one file, so
there's something to look at immediately after `python app.py` without
registering an account and clicking a verification link first.

Usage:
    python scripts/seed.py
"""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SERVER_DIR = os.path.join(PROJECT_ROOT, "server")
sys.path.insert(0, SERVER_DIR)

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models.user import User  # noqa: E402
from models.project import Project  # noqa: E402
from models.project_file import ProjectFile  # noqa: E402

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "DemoPass123!"
DEMO_FILE_CONTENT = 'def greet(name):\n    return f"Hello, {name}!"\n'


def main():
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        existing = User.query.filter_by(email=DEMO_EMAIL).first()
        if existing:
            print(f"Demo user {DEMO_EMAIL} already exists — nothing to do.")
            return

        user = User(email=DEMO_EMAIL, display_name="Demo User", is_email_verified=True)
        user.set_password(DEMO_PASSWORD)
        db.session.add(user)
        db.session.commit()

        project = Project(user_id=user.id, name="Demo Project", description="Seeded by scripts/seed.py")
        db.session.add(project)
        db.session.commit()

        db.session.add(ProjectFile(
            project_id=project.id,
            user_id=user.id,
            filename="main.py",
            folder_path="",
            language="python",
            content=DEMO_FILE_CONTENT,
            size_bytes=len(DEMO_FILE_CONTENT.encode("utf-8")),
        ))
        db.session.commit()

        print(f"Seeded demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Seeded project: {project.name} (id={project.id}) with one file.")


if __name__ == "__main__":
    main()
