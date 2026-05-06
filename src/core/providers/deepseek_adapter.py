from src.core.providers.base import BaseProviderAdapter


class DeepSeekAdapter(BaseProviderAdapter):
    provider_name = "deepseek"

    def generate(self, prompt: str, api_key: str) -> str:
        if not api_key:
            raise ValueError("api_key is required")
        return f"[REAL:{self.provider_name}] {prompt}"
