"""OpenRouter provider stub — see groq.py for the pattern this follows."""
from services.ai.base import AIProvider, AIProviderUnavailable, AIResponse


class OpenRouterProvider(AIProvider):
    name = "openrouter"

    def __init__(self, api_key: str | None = None, model: str = "openai/gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        raise AIProviderUnavailable(
            "OpenRouter provider is not implemented yet — see services/ai/openrouter.py."
        )
