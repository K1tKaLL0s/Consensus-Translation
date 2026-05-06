from src.core.providers.base import BaseProviderAdapter


class GeminiAdapter(BaseProviderAdapter):
    provider_name = "gemini"

    def generate(self, prompt: str, api_key: str) -> str:
        if not api_key:
            raise ValueError("api_key is required")
        return f"[REAL:{self.provider_name}] {prompt}"
