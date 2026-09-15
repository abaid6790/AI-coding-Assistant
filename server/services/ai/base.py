"""
Provider abstraction layer. AIService (service.py) talks to this
interface only — never to a specific vendor's SDK or HTTP shape directly.
Adding a new provider means writing one class here and registering it in
AIService; nothing else in the application (routes, chat, code-review
features) needs to change.

Exception hierarchy is deliberately narrow and meaningful to callers:

  AIProviderError            base class — something went wrong
  ├── AIProviderRetryable    a *specific key* failed in a way that
  │                          trying the NEXT key might fix (rate limit,
  │                          quota, invalid/expired key, transient 5xx).
  │                          Providers raise this internally per-key;
  │                          it should never escape generate().
  └── AIProviderUnavailable  every configured key/provider failed, or the
                             provider isn't configured at all — nothing
                             left to retry.

A plain AIProviderError is used for anything that is NOT a key/provider
problem — a malformed prompt, an unexpected response shape, etc. Per the
spec: never rotate keys for an ordinary bad request, only for rate
limits/quota/transient errors.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class AIProviderError(Exception):
    """Base class for anything that goes wrong talking to an AI provider."""


class AIProviderRetryable(AIProviderError):
    """Raised internally by a provider when ONE key/attempt failed in a
    way that another key might succeed at (429, quota, 5xx, invalid key).
    Callers of AIService should never see this — see AIProviderUnavailable."""


class AIProviderUnavailable(AIProviderError):
    """Every key for this provider was exhausted, or the provider has no
    keys configured at all. Nothing left to retry."""


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str


class AIProvider(ABC):
    """Every provider (Gemini, Groq, OpenRouter, Claude, ...) implements
    this one method. Key rotation, retry, and error classification are
    each provider's own concern — AIService just calls generate() and
    only ever sees AIProviderUnavailable or a plain AIProviderError."""

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AIResponse:
        raise NotImplementedError

    def is_configured(self) -> bool:
        """Whether this provider has the credentials it needs to run at
        all. Used by GET /api/ai/providers so the frontend can show which
        providers are actually usable without leaking key values."""
        return True
