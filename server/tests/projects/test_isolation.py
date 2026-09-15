"""
Phase 3: multi-user data isolation.

The contract under test: User A must never be able to view, modify, or
delete User B's projects, files, or conversations — and a resource that
exists-but-isn't-yours must look identical (404) to one that doesn't
exist at all, so ownership isn't leaked by response code alone.

This suite is deliberately written before Phase 4 builds out full
project/file management, so every route added from here on has to keep
these tests green.
"""
from tests.conftest import register_and_verify, login_as


def _create_project(client, name="Project A"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["project"]


def _create_file(client, project_id, filename="main.py", content="print('hi')"):
    resp = client.post(f"/api/projects/{project_id}/files", json={
        "filename": filename, "content": content, "language": "python",
    })
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["file"]


def _create_conversation(client, title="Chat A"):
    resp = client.post("/api/conversations", json={"title": title})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["conversation"]


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def test_user_b_cannot_view_user_a_project(client):
    register_and_verify(client, "a1@example.com")
    register_and_verify(client, "b1@example.com")

    login_as(client, "a1@example.com")
    project = _create_project(client)
    client.post("/api/auth/logout")

    login_as(client, "b1@example.com")
    resp = client.get(f"/api/projects/{project['id']}")
    assert resp.status_code == 404


def test_user_b_cannot_rename_user_a_project(client):
    register_and_verify(client, "a2@example.com")
    register_and_verify(client, "b2@example.com")

    login_as(client, "a2@example.com")
    project = _create_project(client)
    client.post("/api/auth/logout")

    login_as(client, "b2@example.com")
    resp = client.patch(f"/api/projects/{project['id']}", json={"name": "Hijacked"})
    assert resp.status_code == 404


def test_user_b_cannot_delete_user_a_project(client):
    register_and_verify(client, "a3@example.com")
    register_and_verify(client, "b3@example.com")

    login_as(client, "a3@example.com")
    project = _create_project(client)
    client.post("/api/auth/logout")

    login_as(client, "b3@example.com")
    resp = client.delete(f"/api/projects/{project['id']}")
    assert resp.status_code == 404

    # Confirm it's still there for the actual owner.
    client.post("/api/auth/logout")
    login_as(client, "a3@example.com")
    still_there = client.get(f"/api/projects/{project['id']}")
    assert still_there.status_code == 200


def test_project_list_never_includes_other_users_projects(client):
    register_and_verify(client, "a4@example.com")
    register_and_verify(client, "b4@example.com")

    login_as(client, "a4@example.com")
    _create_project(client, name="A's only project")
    client.post("/api/auth/logout")

    login_as(client, "b4@example.com")
    _create_project(client, name="B's project")
    resp = client.get("/api/projects")
    names = [p["name"] for p in resp.get_json()["projects"]]
    assert names == ["B's project"]


def test_nonexistent_project_is_404_same_as_someone_elses(client):
    register_and_verify(client, "a5@example.com")
    login_as(client, "a5@example.com")

    real_but_not_mine = client.get("/api/projects/does-not-exist")
    assert real_but_not_mine.status_code == 404


def test_project_endpoints_require_authentication(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 401

    resp = client.post("/api/projects", json={"name": "x"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Files (nested under a project — two ownership checks: project AND file)
# ---------------------------------------------------------------------------
def test_user_b_cannot_read_user_a_file_via_a_project_they_dont_own(client):
    register_and_verify(client, "a6@example.com")
    register_and_verify(client, "b6@example.com")

    login_as(client, "a6@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])
    client.post("/api/auth/logout")

    login_as(client, "b6@example.com")
    resp = client.get(f"/api/projects/{project['id']}/files/{file_['id']}")
    assert resp.status_code == 404


def test_user_b_cannot_read_user_a_file_even_via_their_own_project_url(client):
    """B owns a project of their own, and tries to fetch A's file id
    through B's project URL. The file's own user_id must still gate this —
    otherwise a client could probe file ids across projects it owns."""
    register_and_verify(client, "a7@example.com")
    register_and_verify(client, "b7@example.com")

    login_as(client, "a7@example.com")
    project_a = _create_project(client)
    file_a = _create_file(client, project_a["id"])
    client.post("/api/auth/logout")

    login_as(client, "b7@example.com")
    project_b = _create_project(client, name="B's project")
    resp = client.get(f"/api/projects/{project_b['id']}/files/{file_a['id']}")
    assert resp.status_code == 404


def test_user_b_cannot_delete_user_a_file(client):
    register_and_verify(client, "a8@example.com")
    register_and_verify(client, "b8@example.com")

    login_as(client, "a8@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"])
    client.post("/api/auth/logout")

    login_as(client, "b8@example.com")
    resp = client.delete(f"/api/projects/{project['id']}/files/{file_['id']}")
    assert resp.status_code == 404

    client.post("/api/auth/logout")
    login_as(client, "a8@example.com")
    still_there = client.get(f"/api/projects/{project['id']}/files/{file_['id']}")
    assert still_there.status_code == 200


def test_user_b_cannot_create_file_in_user_a_project(client):
    register_and_verify(client, "a9@example.com")
    register_and_verify(client, "b9@example.com")

    login_as(client, "a9@example.com")
    project = _create_project(client)
    client.post("/api/auth/logout")

    login_as(client, "b9@example.com")
    resp = client.post(f"/api/projects/{project['id']}/files", json={
        "filename": "evil.py", "content": "pass",
    })
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------
def test_user_b_cannot_view_user_a_conversation(client):
    register_and_verify(client, "a10@example.com")
    register_and_verify(client, "b10@example.com")

    login_as(client, "a10@example.com")
    convo = _create_conversation(client)
    client.post("/api/auth/logout")

    login_as(client, "b10@example.com")
    resp = client.get(f"/api/conversations/{convo['id']}")
    assert resp.status_code == 404


def test_user_b_cannot_rename_user_a_conversation(client):
    register_and_verify(client, "a11@example.com")
    register_and_verify(client, "b11@example.com")

    login_as(client, "a11@example.com")
    convo = _create_conversation(client)
    client.post("/api/auth/logout")

    login_as(client, "b11@example.com")
    resp = client.patch(f"/api/conversations/{convo['id']}", json={"title": "Hijacked"})
    assert resp.status_code == 404


def test_user_b_cannot_delete_user_a_conversation(client):
    register_and_verify(client, "a12@example.com")
    register_and_verify(client, "b12@example.com")

    login_as(client, "a12@example.com")
    convo = _create_conversation(client)
    client.post("/api/auth/logout")

    login_as(client, "b12@example.com")
    resp = client.delete(f"/api/conversations/{convo['id']}")
    assert resp.status_code == 404


def test_conversation_list_never_includes_other_users_conversations(client):
    register_and_verify(client, "a13@example.com")
    register_and_verify(client, "b13@example.com")

    login_as(client, "a13@example.com")
    _create_conversation(client, title="A's chat")
    client.post("/api/auth/logout")

    login_as(client, "b13@example.com")
    _create_conversation(client, title="B's chat")
    resp = client.get("/api/conversations")
    titles = [c["title"] for c in resp.get_json()["conversations"]]
    assert titles == ["B's chat"]


def test_user_b_cannot_attach_conversation_to_user_a_project(client):
    register_and_verify(client, "a14@example.com")
    register_and_verify(client, "b14@example.com")

    login_as(client, "a14@example.com")
    project = _create_project(client)
    client.post("/api/auth/logout")

    login_as(client, "b14@example.com")
    resp = client.post("/api/conversations", json={"title": "x", "project_id": project["id"]})
    assert resp.status_code == 404


def test_conversation_endpoints_require_authentication(client):
    resp = client.get("/api/conversations")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Never trust a client-supplied user id
# ---------------------------------------------------------------------------
def test_client_supplied_user_id_is_ignored_on_create(client):
    """Even if a malicious client stuffs a foreign user_id into the
    request body, resource creation must always use the session's
    current_user — never a client-supplied field."""
    register_and_verify(client, "a15@example.com")
    register_and_verify(client, "victim15@example.com")
    from models.user import User

    login_as(client, "a15@example.com")
    victim = User.query.filter_by(email="victim15@example.com").first()

    resp = client.post("/api/projects", json={"name": "spoof attempt", "user_id": victim.id})
    assert resp.status_code == 201
    project = resp.get_json()["project"]

    # It must show up under A's own list, not be attributable to the victim.
    listing = client.get("/api/projects")
    ids = [p["id"] for p in listing.get_json()["projects"]]
    assert project["id"] in ids
