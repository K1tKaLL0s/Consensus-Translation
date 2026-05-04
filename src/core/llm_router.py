import os


class LLMRouter:
    _PROVIDER_ENV_MAP = {
        "gpt": "OPENAI_API_KEY",
        "qwen": "QWEN_API_KEY",
        "kimi": "KIMI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "watsonx": "WATSONX_API_KEY",
    }

    def resolve_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in self._PROVIDER_ENV_MAP:
            raise ValueError(f"Unknown provider: {provider}")
        return normalized

    def _has_key(self, provider: str) -> bool:
        resolved = self.resolve_provider(provider)
        env_name = self._PROVIDER_ENV_MAP[resolved]
        return bool(os.getenv(env_name))

    def generate(self, provider: str, prompt: str) -> str:
        resolved = self.resolve_provider(provider)
        if not self._has_key(resolved):
            return f"[MOCK:{resolved}] {prompt}"
        return f"[REAL:{resolved}] {prompt}"
