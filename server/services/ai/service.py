"""
AIService is the ONLY thing the rest of the app (routes, chat, code
review, etc.) should import from services.ai. It hides which
providers exist, which are configured, and how each one handles its own
retries — callers just say "generate this" and optionally which provider
to use.

Usage:

    ai_service = AIService(current_app.config)
    response = ai_service.generate("Explain this function...")
    # response.text, response.provider, response.model
"""
from services.ai.base import AIProvider, AIProviderUnavailable
from services.ai.providers.gemini import GeminiProvider
from services.ai.providers.groq import GroqProvider
from services.ai.providers.openrouter import OpenRouterProvider
from services.ai.providers.claude import ClaudeProvider


class AIService:
    def __init__(self, config: dict, default_provider: str = "gemini"):
        self.default_provider = default_provider
        self.providers: dict[str, AIProvider] = self._build_providers(config)

    @staticmethod
    def _build_providers(config: dict) -> dict[str, AIProvider]:
        # Adding a real provider is: import it above, instantiate it here
        # with its config key(s). Nothing else in the app changes.
        return {
            "gemini": GeminiProvider(config.get("GEMINI_API_KEYS", [])),
            "groq": GroqProvider(config.get("GROQ_API_KEY")),
            "openrouter": OpenRouterProvider(config.get("OPENROUTER_API_KEY")),
            "claude": ClaudeProvider(config.get("ANTHROPIC_API_KEY")),
        }

    def list_providers(self) -> list[dict]:
        """Safe-to-serialize provider status for GET /api/ai/providers —
        names and configured/not, never key values."""
        return [
            {
                "name": name,
                "configured": provider.is_configured(),
                "is_default": name == self.default_provider,
            }
            for name, provider in self.providers.items()
        ]

    def generate(self, prompt: str, provider: str | None = None, **kwargs):
        provider_name = provider or self.default_provider
        provider_obj = self.providers.get(provider_name)

        if provider_obj is None:
            raise AIProviderUnavailable(f"Unknown AI provider: '{provider_name}'.")
        if not provider_obj.is_configured():
            raise AIProviderUnavailable(f"Provider '{provider_name}' is not configured.")

        return provider_obj.generate(prompt, **kwargs)
