"""Anthropic Claude provider stub — see groq.py for the pattern this follows."""
from services.ai.base import AIProvider, AIProviderUnavailable, AIResponse


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        raise AIProviderUnavailable(
            "Claude provider is not implemented yet — see services/ai/claude.py."
        )
