from src.core.providers.base import BaseProviderAdapter


class WatsonXAdapter(BaseProviderAdapter):
    provider_name = "watsonx"

    def generate(self, prompt: str, api_key: str) -> str:
        if not api_key:
            raise ValueError("api_key is required")
        return f"[REAL:{self.provider_name}] {prompt}"
