from unittest.mock import patch

import pytest

from services.ai.base import AIProviderUnavailable
from services.ai.service import AIService


def test_list_providers_reports_configured_status_without_leaking_keys():
    service = AIService({
        "GEMINI_API_KEYS": ["k1", "k2"],
        "GROQ_API_KEY": None,
        "OPENROUTER_API_KEY": None,
        "ANTHROPIC_API_KEY": None,
    })
    statuses = {p["name"]: p for p in service.list_providers()}

    assert statuses["gemini"]["configured"] is True
    assert statuses["gemini"]["is_default"] is True
    assert statuses["groq"]["configured"] is False
    assert statuses["openrouter"]["configured"] is False
    assert statuses["claude"]["configured"] is False

    # No key material anywhere in the serialized output.
    import json
    dumped = json.dumps(service.list_providers())
    assert "k1" not in dumped and "k2" not in dumped


def test_generate_dispatches_to_default_provider():
    service = AIService({"GEMINI_API_KEYS": ["k1"]})
    with patch("services.ai.providers.gemini.requests.post") as mock_post:
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.status_code = 200
        resp.ok = True
        resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "hi there"}]}}]}
        mock_post.return_value = resp

        result = service.generate("hello")
        assert result.text == "hi there"
        assert result.provider == "gemini"


def test_generate_unconfigured_provider_raises():
    service = AIService({"GEMINI_API_KEYS": []})
    with pytest.raises(AIProviderUnavailable):
        service.generate("hello", provider="gemini")


def test_generate_unknown_provider_raises():
    service = AIService({"GEMINI_API_KEYS": ["k1"]})
    with pytest.raises(AIProviderUnavailable):
        service.generate("hello", provider="not-a-real-provider")


def test_stub_providers_raise_not_implemented_when_selected():
    service = AIService({
        "GEMINI_API_KEYS": [],
        "GROQ_API_KEY": "fake-key",  # "configured" but generate() is still a stub
    })
    with pytest.raises(AIProviderUnavailable):
        service.generate("hello", provider="groq")
