import os

from src.services.llm_config_service import default_llm_config_service


class LLMRouter:
    _PROVIDER_ENV_MAP = {
        "gpt": "OPENAI_API_KEY",
        "qwen": "QWEN_API_KEY",
        "kimi": "KIMI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "watsonx": "WATSONX_API_KEY",
    }

    def __init__(self, allow_mock_fallback: bool | None = None) -> None:
        if allow_mock_fallback is None:
            allow_mock_fallback = self._allow_mock_fallback_from_env()
        self.allow_mock_fallback = allow_mock_fallback

    def _allow_mock_fallback_from_env(self) -> bool:
        raw = os.getenv("MAATCS_ALLOW_MOCK_FALLBACK")
        if raw is None:
            return True

        normalized = raw.strip().lower()
        if normalized in {"0", "false", "no", "off"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
        return True

    def resolve_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in self._PROVIDER_ENV_MAP:
            raise ValueError(f"Unknown provider: {provider}")
        return normalized

    def _has_key(self, provider: str) -> bool:
        resolved = self.resolve_provider(provider)
        env_name = self._PROVIDER_ENV_MAP[resolved]

        try:
            status = default_llm_config_service().load()
        except FileNotFoundError:
            status = None

        if status and status.get("provider") == resolved and status.get("api_key"):
            return True
        return bool(os.getenv(env_name))

    def generate(self, provider: str, prompt: str) -> str:
        resolved = self.resolve_provider(provider)
        if not self._has_key(resolved):
            if not self.allow_mock_fallback:
                env_name = self._PROVIDER_ENV_MAP[resolved]
                raise ValueError(
                    f"{env_name} is required when mock fallback is disabled"
                )
            return f"[MOCK:{resolved}] {prompt}"
        return f"[REAL:{resolved}] {prompt}"
