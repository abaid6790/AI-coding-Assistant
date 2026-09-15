"""
Gemini provider with API key rotation.

Rotation rule (per spec): switch to the next key on rate limit, quota
exhaustion, an invalid/rejected key, or a transient (5xx) provider error.
Do NOT rotate for an ordinary bad request (400) — that's a problem with
the prompt/payload, not the key, and every key would fail the same way.
"""
import requests

from services.ai.base import (
    AIProvider,
    AIProviderError,
    AIProviderRetryable,
    AIProviderUnavailable,
    AIResponse,
)

DEFAULT_MODEL = "gemini-1.5-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT_SECONDS = 30

# Status codes that mean "this key/attempt failed, but a different key
# might succeed" — rate limit, quota, transient server errors, and an
# invalid/forbidden key. Everything else (400 bad request, etc.) is a
# real error that rotating keys would not fix.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_INVALID_KEY_STATUS_CODES = {401, 403}


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_keys: list[str], model: str = DEFAULT_MODEL):
        self.api_keys = [k for k in api_keys if k]
        self.model = model
        # Sticky index: once a key works, keep using it rather than
        # starting from key 1 every call — avoids hammering an
        # already-exhausted key repeatedly across requests.
        self._key_index = 0

    def is_configured(self) -> bool:
        return len(self.api_keys) > 0

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AIResponse:
        if not self.api_keys:
            raise AIProviderUnavailable("No Gemini API keys are configured.")

        n = len(self.api_keys)
        last_error: Exception | None = None

        for offset in range(n):
            idx = (self._key_index + offset) % n
            key = self.api_keys[idx]
            try:
                text = self._call(key, prompt, system, temperature, max_tokens)
            except AIProviderRetryable as exc:
                last_error = exc
                continue  # try the next key
            else:
                self._key_index = idx  # stick with the key that worked
                return AIResponse(text=text, provider=self.name, model=self.model)

        raise AIProviderUnavailable(
            f"All {n} configured Gemini API key(s) are rate-limited, invalid, or unavailable."
        ) from last_error

    def _call(
        self, api_key: str, prompt: str, system: str | None, temperature: float, max_tokens: int
    ) -> str:
        url = f"{API_BASE}/models/{self.model}:generateContent?key={api_key}"
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        try:
            resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            # Network-level failure (DNS, timeout, connection refused) —
            # treat as retryable since it says nothing about the key
            # itself and another key might route through fine.
            raise AIProviderRetryable(f"Network error calling Gemini: {exc}") from exc

        if resp.status_code in _RETRYABLE_STATUS_CODES:
            raise AIProviderRetryable(f"Gemini returned {resp.status_code} (retryable): {resp.text[:200]}")

        if resp.status_code in _INVALID_KEY_STATUS_CODES:
            raise AIProviderRetryable(f"Gemini rejected this key ({resp.status_code}): {resp.text[:200]}")

        if not resp.ok:
            # A genuine 4xx that isn't a key problem (e.g. 400 bad
            # request) — rotating keys would not help, so surface it
            # immediately instead of burning through every key first.
            raise AIProviderError(f"Gemini request failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Unexpected response shape from Gemini.") from exc
