from unittest.mock import patch

from tests.conftest import register_and_verify, login_as
from services.ai.base import AIResponse, AIProviderUnavailable, AIProviderError


def _create_conversation(client, title="New conversation", project_id=None):
    payload = {"title": title}
    if project_id:
        payload["project_id"] = project_id
    resp = client.post("/api/conversations", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["conversation"]


def _create_project(client, name="P"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.get_json()["project"]


def _create_file(client, project_id, filename="app.py", content="print(1)"):
    resp = client.post(f"/api/projects/{project_id}/files", json={"filename": filename, "content": content})
    assert resp.status_code == 201
    return resp.get_json()["file"]


def _mock_ai(text="Hello from the assistant", provider="gemini", model="gemini-1.5-flash"):
    return patch(
        "services.ai.service.AIService.generate",
        return_value=AIResponse(text=text, provider=provider, model=model),
    )


# ---------------------------------------------------------------------------
# Sending a message
# ---------------------------------------------------------------------------
def test_send_message_persists_both_sides_of_exchange(client):
    register_and_verify(client, "chat1@example.com")
    login_as(client, "chat1@example.com")
    convo = _create_conversation(client)

    with _mock_ai("42"):
        resp = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "What is the answer?"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user_message"]["content"] == "What is the answer?"
    assert body["assistant_message"]["content"] == "42"
    assert body["assistant_message"]["provider"] == "gemini"

    fetched = client.get(f"/api/conversations/{convo['id']}")
    messages = fetched.get_json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_first_message_sets_conversation_title(client):
    register_and_verify(client, "chat2@example.com")
    login_as(client, "chat2@example.com")
    convo = _create_conversation(client)

    with _mock_ai():
        client.post(f"/api/conversations/{convo['id']}/messages", json={
            "content": "How do I reverse a linked list in Python?"
        })

    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.get_json()["conversation"]["title"] == "How do I reverse a linked list in Python?"


def test_second_message_does_not_overwrite_title(client):
    register_and_verify(client, "chat3@example.com")
    login_as(client, "chat3@example.com")
    convo = _create_conversation(client)

    with _mock_ai():
        client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "first question"})
        client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "second question"})

    fetched = client.get(f"/api/conversations/{convo['id']}")
    assert fetched.get_json()["conversation"]["title"] == "first question"


def test_empty_message_rejected(client):
    register_and_verify(client, "chat4@example.com")
    login_as(client, "chat4@example.com")
    convo = _create_conversation(client)

    resp = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "   "})
    assert resp.status_code == 400


def test_user_message_persisted_even_if_ai_call_fails(client):
    """The user's message must survive a provider outage — only the
    assistant reply is missing, not their input."""
    register_and_verify(client, "chat5@example.com")
    login_as(client, "chat5@example.com")
    convo = _create_conversation(client)

    with patch("services.ai.service.AIService.generate", side_effect=AIProviderUnavailable("no keys")):
        resp = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "will this survive?"})

    assert resp.status_code == 503

    fetched = client.get(f"/api/conversations/{convo['id']}")
    messages = fetched.get_json()["messages"]
    assert len(messages) == 1
    assert messages[0]["content"] == "will this survive?"


def test_provider_error_returns_502(client):
    register_and_verify(client, "chat6@example.com")
    login_as(client, "chat6@example.com")
    convo = _create_conversation(client)

    with patch("services.ai.service.AIService.generate", side_effect=AIProviderError("bad prompt")):
        resp = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "hi"})

    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# Context selection (current file / selection)
# ---------------------------------------------------------------------------
def test_message_with_file_context_includes_file_in_prompt(client):
    register_and_verify(client, "chat7@example.com")
    login_as(client, "chat7@example.com")
    project = _create_project(client)
    file_ = _create_file(client, project["id"], content="def add(a, b):\n    return a + b")
    convo = _create_conversation(client, project_id=project["id"])

    with patch("services.ai.service.AIService.generate") as mock_generate:
        mock_generate.return_value = AIResponse(text="ok", provider="gemini", model="m")
        client.post(f"/api/conversations/{convo['id']}/messages", json={
            "content": "explain this", "file_id": file_["id"],
        })

    prompt_arg = mock_generate.call_args[0][0]
    assert "def add(a, b):" in prompt_arg


def test_file_from_different_project_is_ignored_as_context(client):
    """A file_id that doesn't belong to the conversation's project must
    not leak its content into the prompt."""
    register_and_verify(client, "chat8@example.com")
    login_as(client, "chat8@example.com")
    project_a = _create_project(client, name="A")
    project_b = _create_project(client, name="B")
    file_b = _create_file(client, project_b["id"], content="TOP SECRET CONTENT")
    convo = _create_conversation(client, project_id=project_a["id"])

    with patch("services.ai.service.AIService.generate") as mock_generate:
        mock_generate.return_value = AIResponse(text="ok", provider="gemini", model="m")
        client.post(f"/api/conversations/{convo['id']}/messages", json={
            "content": "explain this", "file_id": file_b["id"],
        })

    prompt_arg = mock_generate.call_args[0][0]
    assert "TOP SECRET CONTENT" not in prompt_arg


def test_message_with_selection_includes_selection_in_prompt(client):
    register_and_verify(client, "chat9@example.com")
    login_as(client, "chat9@example.com")
    convo = _create_conversation(client)

    with patch("services.ai.service.AIService.generate") as mock_generate:
        mock_generate.return_value = AIResponse(text="ok", provider="gemini", model="m")
        client.post(f"/api/conversations/{convo['id']}/messages", json={
            "content": "what does this do?", "selection": "x = [i**2 for i in range(10)]",
        })

    prompt_arg = mock_generate.call_args[0][0]
    assert "x = [i**2 for i in range(10)]" in prompt_arg


# ---------------------------------------------------------------------------
# Regenerate
# ---------------------------------------------------------------------------
def test_regenerate_replaces_assistant_message_in_place(client):
    register_and_verify(client, "chat10@example.com")
    login_as(client, "chat10@example.com")
    convo = _create_conversation(client)

    with _mock_ai("first answer"):
        send = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "hi"})
    assistant_id = send.get_json()["assistant_message"]["id"]

    with _mock_ai("regenerated answer"):
        resp = client.post(f"/api/conversations/{convo['id']}/messages/{assistant_id}/regenerate", json={})

    assert resp.status_code == 200
    assert resp.get_json()["assistant_message"]["content"] == "regenerated answer"

    fetched = client.get(f"/api/conversations/{convo['id']}")
    messages = fetched.get_json()["messages"]
    assert len(messages) == 2  # replaced in place, not appended
    assert messages[-1]["content"] == "regenerated answer"


def test_regenerate_on_user_message_rejected(client):
    register_and_verify(client, "chat11@example.com")
    login_as(client, "chat11@example.com")
    convo = _create_conversation(client)

    with _mock_ai():
        send = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "hi"})
    user_id = send.get_json()["user_message"]["id"]

    resp = client.post(f"/api/conversations/{convo['id']}/messages/{user_id}/regenerate", json={})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------
def test_user_b_cannot_send_message_in_user_a_conversation(client):
    register_and_verify(client, "chatiso_a@example.com")
    register_and_verify(client, "chatiso_b@example.com")

    login_as(client, "chatiso_a@example.com")
    convo = _create_conversation(client)
    client.post("/api/auth/logout")

    login_as(client, "chatiso_b@example.com")
    resp = client.post(f"/api/conversations/{convo['id']}/messages", json={"content": "hijack"})
    assert resp.status_code == 404


def test_message_endpoints_require_authentication(client):
    resp = client.post("/api/conversations/does-not-exist/messages", json={"content": "hi"})
    assert resp.status_code == 401
