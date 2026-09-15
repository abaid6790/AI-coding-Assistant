"""
Groq provider — not implemented yet. This file exists to show exactly
what "adding a provider" means in this architecture: one class matching
the AIProvider interface, registered in AIService. When you're ready to
wire this up for real:

  1. Fill in _call() following gemini.py's pattern (Groq's API is
     OpenAI-compatible, so this is usually a smaller diff than Gemini's).
  2. Add GROQ_API_KEY to config.py and .env.example.
  3. Register it in AIService._build_providers() in service.py.

Nothing else in the app — routes, chat, code-review features — needs to
change, since they all talk to AIService, not to a specific provider.
"""
from services.ai.base import AIProvider, AIProviderUnavailable, AIResponse


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self, api_key: str | None = None, model: str = "llama-3.1-70b-versatile"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, **kwargs) -> AIResponse:
        raise AIProviderUnavailable(
            "Groq provider is not implemented yet — see services/ai/groq.py."
        )
