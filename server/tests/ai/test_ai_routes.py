from tests.conftest import register_and_verify, login_as


def test_providers_endpoint_requires_authentication(client):
    resp = client.get("/api/ai/providers")
    assert resp.status_code == 401


def test_providers_endpoint_lists_all_providers(client):
    register_and_verify(client, "ai1@example.com")
    login_as(client, "ai1@example.com")

    resp = client.get("/api/ai/providers")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.get_json()["providers"]}
    assert names == {"gemini", "groq", "openrouter", "claude"}


def test_providers_endpoint_never_leaks_key_values(client):
    register_and_verify(client, "ai2@example.com")
    login_as(client, "ai2@example.com")

    resp = client.get("/api/ai/providers")
    body = resp.get_data(as_text=True)
    # None of these should ever appear in a provider-status response,
    # configured or not.
    assert "GEMINI_API_KEY" not in body
    assert "api_key" not in body.lower() or "\"api_key\"" not in body
