"""
These tests mock requests.post rather than hitting the real Gemini API —
there's no network egress to Google's API from this environment, and
more importantly, the whole point of this suite is to pin down the
*rotation* logic deterministically, which requires controlling exactly
which status code each key "returns" on each call.
"""
from unittest.mock import patch, MagicMock

import pytest

from services.ai.base import AIProviderError, AIProviderUnavailable
from services.ai.providers.gemini import GeminiProvider


def _mock_response(status_code=200, json_data=None, text="error"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.text = text
    resp.json.return_value = json_data or {}
    return resp


def _success_json(text="Hello from Gemini"):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


@patch("services.ai.providers.gemini.requests.post")
def test_generate_success_on_first_key(mock_post):
    mock_post.return_value = _mock_response(200, _success_json("42 is the answer"))

    provider = GeminiProvider(api_keys=["key-1", "key-2"])
    result = provider.generate("What is the answer?")

    assert result.text == "42 is the answer"
    assert result.provider == "gemini"
    assert mock_post.call_count == 1


@patch("services.ai.providers.gemini.requests.post")
def test_rotates_to_next_key_on_429(mock_post):
    mock_post.side_effect = [
        _mock_response(429, text="rate limited"),
        _mock_response(200, _success_json("from key 2")),
    ]

    provider = GeminiProvider(api_keys=["key-1", "key-2"])
    result = provider.generate("hi")

    assert result.text == "from key 2"
    assert mock_post.call_count == 2


@patch("services.ai.providers.gemini.requests.post")
def test_rotates_on_invalid_key_403(mock_post):
    mock_post.side_effect = [
        _mock_response(403, text="forbidden"),
        _mock_response(200, _success_json("from key 2")),
    ]

    provider = GeminiProvider(api_keys=["bad-key", "good-key"])
    result = provider.generate("hi")

    assert result.text == "from key 2"


@patch("services.ai.providers.gemini.requests.post")
def test_rotates_on_transient_5xx(mock_post):
    mock_post.side_effect = [
        _mock_response(503, text="temporarily unavailable"),
        _mock_response(200, _success_json("recovered")),
    ]

    provider = GeminiProvider(api_keys=["key-1", "key-2"])
    result = provider.generate("hi")
    assert result.text == "recovered"


@patch("services.ai.providers.gemini.requests.post")
def test_all_keys_exhausted_raises_unavailable(mock_post):
    mock_post.side_effect = [
        _mock_response(429, text="rate limited"),
        _mock_response(429, text="rate limited"),
        _mock_response(429, text="rate limited"),
    ]

    provider = GeminiProvider(api_keys=["k1", "k2", "k3"])
    with pytest.raises(AIProviderUnavailable):
        provider.generate("hi")

    assert mock_post.call_count == 3


@patch("services.ai.providers.gemini.requests.post")
def test_does_not_rotate_on_ordinary_bad_request(mock_post):
    """A 400 means the prompt/payload itself is bad — every key would
    fail identically, so we must NOT burn through all keys retrying it."""
    mock_post.return_value = _mock_response(400, text="bad request: empty prompt")

    provider = GeminiProvider(api_keys=["key-1", "key-2", "key-3"])
    with pytest.raises(AIProviderError):
        provider.generate("")

    assert mock_post.call_count == 1  # never tried key-2 or key-3


@patch("services.ai.providers.gemini.requests.post")
def test_sticky_key_reused_on_next_call(mock_post):
    """Once key-2 works, the next call should try key-2 first, not
    restart from key-1 and re-trigger its rate limit every time."""
    mock_post.side_effect = [
        _mock_response(429, text="rate limited"),        # call 1: key-1 fails
        _mock_response(200, _success_json("first")),      # call 1: key-2 works
        _mock_response(200, _success_json("second")),      # call 2: key-2 again, straight away
    ]

    provider = GeminiProvider(api_keys=["key-1", "key-2"])
    first = provider.generate("hi")
    second = provider.generate("hi again")

    assert first.text == "first"
    assert second.text == "second"
    assert mock_post.call_count == 3  # not 4 — call 2 didn't retry key-1


def test_no_keys_configured_raises_unavailable():
    provider = GeminiProvider(api_keys=[])
    with pytest.raises(AIProviderUnavailable):
        provider.generate("hi")


@patch("services.ai.providers.gemini.requests.post")
def test_malformed_response_shape_raises_error(mock_post):
    mock_post.return_value = _mock_response(200, json_data={"unexpected": "shape"})

    provider = GeminiProvider(api_keys=["key-1"])
    with pytest.raises(AIProviderError):
        provider.generate("hi")


@patch("services.ai.providers.gemini.requests.post")
def test_network_error_is_retryable_across_keys(mock_post):
    import requests as requests_module

    mock_post.side_effect = [
        requests_module.ConnectionError("DNS failure"),
        _mock_response(200, _success_json("recovered after network blip")),
    ]

    provider = GeminiProvider(api_keys=["key-1", "key-2"])
    result = provider.generate("hi")
    assert result.text == "recovered after network blip"
