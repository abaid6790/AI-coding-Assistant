from tests.conftest import register_and_verify, login_as


def _create_project(client, name="Project A"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["project"]


def _create_file(client, project_id, filename="main.py", folder_path="", content="print('hi')"):
    resp = client.post(f"/api/projects/{project_id}/files", json={
        "filename": filename, "folder_path": folder_path, "content": content, "language": "python",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["file"]


# ---------------------------------------------------------------------------
# Project search
# ---------------------------------------------------------------------------
def test_project_search_filters_by_name(client):
    register_and_verify(client, "p1@example.com")
    login_as(client, "p1@example.com")
    _create_project(client, name="Warehouse Tracker")
    _create_project(client, name="Sports Analytics")

    resp = client.get("/api/projects?search=warehouse")
    names = [p["name"] for p in resp.get_json()["projects"]]
    assert names == ["Warehouse Tracker"]


# ---------------------------------------------------------------------------
# File CRUD
# ---------------------------------------------------------------------------
def test_create_file_rejects_duplicate_name_in_same_folder(client):
    register_and_verify(client, "f1@example.com")
    login_as(client, "f1@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], filename="app.py")

    resp = client.post(f"/api/projects/{project['id']}/files", json={"filename": "app.py"})
    assert resp.status_code == 409


def test_create_file_allows_same_name_in_different_folder(client):
    register_and_verify(client, "f2@example.com")
    login_as(client, "f2@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], filename="__init__.py", folder_path="pkg_a")
    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "__init__.py", "folder_path": "pkg_b",
    })
    assert resp.status_code == 201


def test_update_file_content(client):
    register_and_verify(client, "f3@example.com")
    login_as(client, "f3@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])

    resp = client.patch(f"/api/projects/{project['id']}/files/{file_['id']}", json={
        "content": "print('updated')",
    })
    assert resp.status_code == 200
    assert resp.get_json()["file"]["size_bytes"] == len("print('updated')".encode("utf-8"))


def test_update_file_rename_rejects_collision(client):
    register_and_verify(client, "f4@example.com")
    login_as(client, "f4@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], filename="a.py")
    b = _create_file(client, project["id"], filename="b.py")

    resp = client.patch(f"/api/projects/{project['id']}/files/{b['id']}", json={"filename": "a.py"})
    assert resp.status_code == 409


def test_update_file_move_to_folder(client):
    register_and_verify(client, "f5@example.com")
    login_as(client, "f5@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"], filename="a.py")

    resp = client.patch(f"/api/projects/{project['id']}/files/{file_['id']}", json={
        "folder_path": "src",
    })
    assert resp.status_code == 200
    assert resp.get_json()["file"]["folder_path"] == "src"


def test_file_search_filters_by_filename(client):
    register_and_verify(client, "f6@example.com")
    login_as(client, "f6@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], filename="models.py")
    _create_file(client, project["id"], filename="views.py")

    resp = client.get(f"/api/projects/{project['id']}/files?search=model")
    names = [f["filename"] for f in resp.get_json()["files"]]
    assert names == ["models.py"]


def test_file_content_size_limit_enforced(client):
    register_and_verify(client, "f7@example.com")
    login_as(client, "f7@example.com")
    project = _create_project(client)

    huge = "x" * (1024 * 1024 + 1)
    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "huge.txt", "content": huge,
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
def test_list_folders_returns_distinct_paths(client):
    register_and_verify(client, "fo1@example.com")
    login_as(client, "fo1@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], filename="a.py", folder_path="src")
    _create_file(client, project["id"], filename="b.py", folder_path="src")
    _create_file(client, project["id"], filename="c.py", folder_path="tests")
    _create_file(client, project["id"], filename="root.py", folder_path="")

    resp = client.get(f"/api/projects/{project['id']}/folders")
    assert resp.get_json()["folders"] == ["src", "tests"]


def test_rename_folder_moves_all_files_and_subfolders(client):
    register_and_verify(client, "fo2@example.com")
    login_as(client, "fo2@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], filename="utils.py", folder_path="src/helpers")
    _create_file(client, project["id"], filename="main.py", folder_path="src")

    resp = client.patch(f"/api/projects/{project['id']}/folders", json={
        "old_path": "src", "new_path": "app",
    })
    assert resp.status_code == 200
    assert resp.get_json()["moved"] == 2

    files_resp = client.get(f"/api/projects/{project['id']}/files")
    paths = sorted(f["folder_path"] for f in files_resp.get_json()["files"])
    assert paths == ["app", "app/helpers"]


# ---------------------------------------------------------------------------
# Isolation for the new Phase 4 endpoints
# ---------------------------------------------------------------------------
def test_user_b_cannot_update_user_a_file(client):
    register_and_verify(client, "iso1a@example.com")
    register_and_verify(client, "iso1b@example.com")

    login_as(client, "iso1a@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])
    client.post("/api/auth/logout")

    login_as(client, "iso1b@example.com")
    resp = client.patch(f"/api/projects/{project['id']}/files/{file_['id']}", json={"content": "hacked"})
    assert resp.status_code == 404


def test_user_b_cannot_rename_user_a_folder(client):
    register_and_verify(client, "iso2a@example.com")
    register_and_verify(client, "iso2b@example.com")

    login_as(client, "iso2a@example.com")
    project = _create_project(client)
    _create_file(client, project["id"], folder_path="secrets")
    client.post("/api/auth/logout")

    login_as(client, "iso2b@example.com")
    resp = client.patch(f"/api/projects/{project['id']}/folders", json={
        "old_path": "secrets", "new_path": "pwned",
    })
    assert resp.status_code == 404


def test_user_b_project_search_never_matches_user_a_projects(client):
    register_and_verify(client, "iso3a@example.com")
    register_and_verify(client, "iso3b@example.com")

    login_as(client, "iso3a@example.com")
    _create_project(client, name="Confidential Roadmap")
    client.post("/api/auth/logout")

    login_as(client, "iso3b@example.com")
    resp = client.get("/api/projects?search=confidential")
    assert resp.get_json()["projects"] == []
