from tests.conftest import register_and_verify, login_as
from utils.validation import is_valid_filename, is_valid_folder_path, validate_file_extension


def _create_project(client, name="P"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["project"]


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------
def test_is_valid_filename_rejects_path_separators():
    assert is_valid_filename("../../etc/passwd") is False
    assert is_valid_filename("sub/dir/file.py") is False
    assert is_valid_filename("a\\b.py") is False


def test_is_valid_filename_rejects_dot_and_dotdot():
    assert is_valid_filename(".") is False
    assert is_valid_filename("..") is False


def test_is_valid_filename_rejects_null_byte_and_whitespace():
    assert is_valid_filename("file\x00.py") is False
    assert is_valid_filename(" file.py") is False
    assert is_valid_filename("file.py ") is False


def test_is_valid_filename_accepts_normal_names():
    assert is_valid_filename("app.py") is True
    assert is_valid_filename("Dockerfile") is True
    assert is_valid_filename("my-file_v2.test.js") is True


def test_is_valid_folder_path_rejects_traversal_segments():
    assert is_valid_folder_path("src/../etc") is False
    assert is_valid_folder_path("..") is False
    assert is_valid_folder_path("a//b") is False  # empty segment


def test_is_valid_folder_path_accepts_normal_paths():
    assert is_valid_folder_path("") is True
    assert is_valid_folder_path("src") is True
    assert is_valid_folder_path("src/utils/helpers") is True


def test_validate_file_extension_allows_known_extensions():
    allowed = {"py", "js", "json"}
    assert validate_file_extension("main.py", allowed) is True
    assert validate_file_extension("data.JSON", allowed) is True  # case-insensitive


def test_validate_file_extension_rejects_unknown_extensions():
    allowed = {"py", "js", "json"}
    assert validate_file_extension("virus.exe", allowed) is False
    assert validate_file_extension("script.sh", allowed) is False


def test_validate_file_extension_allows_known_extensionless_names():
    assert validate_file_extension("Dockerfile", {"py"}) is True
    assert validate_file_extension("makefile", {"py"}) is True


def test_validate_file_extension_rejects_unknown_extensionless_names():
    assert validate_file_extension("randomfile", {"py"}) is False


# ---------------------------------------------------------------------------
# Route-level enforcement
# ---------------------------------------------------------------------------
def test_create_file_rejects_path_traversal_in_filename(client):
    register_and_verify(client, "fv1@example.com")
    login_as(client, "fv1@example.com")
    project = _create_project(client)

    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "../../etc/passwd", "content": "x",
    })
    assert resp.status_code == 400


def test_create_file_rejects_traversal_in_folder_path(client):
    register_and_verify(client, "fv2@example.com")
    login_as(client, "fv2@example.com")
    project = _create_project(client)

    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "app.py", "folder_path": "../../secrets", "content": "x",
    })
    assert resp.status_code == 400


def test_create_file_rejects_disallowed_extension(client):
    register_and_verify(client, "fv3@example.com")
    login_as(client, "fv3@example.com")
    project = _create_project(client)

    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "malware.exe", "content": "x",
    })
    assert resp.status_code == 400
    assert resp.get_json()["field_errors"]["filename"] == "extension_not_allowed"


def test_create_file_allows_dockerfile_without_extension(client):
    register_and_verify(client, "fv4@example.com")
    login_as(client, "fv4@example.com")
    project = _create_project(client)

    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "Dockerfile", "content": "FROM python:3.12",
    })
    assert resp.status_code == 201


def test_update_file_rejects_renaming_to_traversal_filename(client):
    register_and_verify(client, "fv5@example.com")
    login_as(client, "fv5@example.com")
    project = _create_project(client)
    created = client.post(f"/api/projects/{project['id']}/files", json={"filename": "a.py", "content": "x"})
    file_id = created.get_json()["file"]["id"]

    resp = client.patch(f"/api/projects/{project['id']}/files/{file_id}", json={"filename": "../evil.py"})
    assert resp.status_code == 400


def test_update_file_rejects_renaming_to_disallowed_extension(client):
    register_and_verify(client, "fv6@example.com")
    login_as(client, "fv6@example.com")
    project = _create_project(client)
    created = client.post(f"/api/projects/{project['id']}/files", json={"filename": "a.py", "content": "x"})
    file_id = created.get_json()["file"]["id"]

    resp = client.patch(f"/api/projects/{project['id']}/files/{file_id}", json={"filename": "a.exe"})
    assert resp.status_code == 400


def test_rename_folder_rejects_traversal_in_new_path(client):
    register_and_verify(client, "fv7@example.com")
    login_as(client, "fv7@example.com")
    project = _create_project(client)
    client.post(f"/api/projects/{project['id']}/files", json={"filename": "a.py", "folder_path": "src", "content": "x"})

    resp = client.patch(f"/api/projects/{project['id']}/folders", json={
        "old_path": "src", "new_path": "../../outside",
    })
    assert resp.status_code == 400
