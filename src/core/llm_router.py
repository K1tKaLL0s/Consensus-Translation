import os

from src.core.providers import PROVIDER_ADAPTERS
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
        return bool(self._get_api_key(provider))

    def _get_api_key(self, provider: str) -> str | None:
        resolved = self.resolve_provider(provider)
        env_name = self._PROVIDER_ENV_MAP[resolved]

        try:
            status = default_llm_config_service().load()
        except FileNotFoundError:
            status = None

        if status and status.get("provider") == resolved and status.get("api_key"):
            return str(status.get("api_key"))

        env_value = os.getenv(env_name)
        if env_value:
            return env_value
        return None

    def _dispatch_provider(self, provider: str, prompt: str, api_key: str) -> str:
        adapter = PROVIDER_ADAPTERS.get(provider)
        if adapter is None:
            raise NotImplementedError(f"No provider adapter registered for: {provider}")
        return adapter.generate(prompt=prompt, api_key=api_key)

    def generate(self, provider: str, prompt: str) -> str:
        resolved = self.resolve_provider(provider)
        api_key = self._get_api_key(resolved)

        if not api_key:
            if not self.allow_mock_fallback:
                env_name = self._PROVIDER_ENV_MAP[resolved]
                raise ValueError(
                    f"{env_name} is required when mock fallback is disabled"
                )
            return f"[MOCK:{resolved}] {prompt}"

        try:
            return self._dispatch_provider(resolved, prompt, api_key)
        except Exception:
            if self.allow_mock_fallback:
                return f"[MOCK:{resolved}] {prompt}"
            raise
