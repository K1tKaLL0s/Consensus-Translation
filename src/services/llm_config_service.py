import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_LLM_PROVIDERS = ("gpt", "qwen", "kimi", "deepseek", "gemini", "watsonx")


def resolve_llm_config_path() -> Path:
    raw = os.getenv("MAATCS_LLM_CONFIG_PATH")
    if raw:
        return Path(raw)
    return Path(".runtime") / "llm_config.json"


@dataclass
class LLMConfigService:
    config_path: Path

    def save(self, provider: str, model: str, api_key: str) -> dict[str, object]:
        normalized_provider = provider.strip().lower()
        cleaned_model = model.strip()
        cleaned_key = api_key.strip()

        if normalized_provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError("unsupported provider")
        if not cleaned_model:
            raise ValueError("model must not be blank")
        if not cleaned_key:
            raise ValueError("api_key must not be blank")

        payload = {
            "provider": normalized_provider,
            "model": cleaned_model,
            "api_key": cleaned_key,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return self.get_status()

    def load(self) -> dict[str, str]:
        if not self.config_path.exists():
            raise FileNotFoundError("llm config not found")
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def clear(self) -> dict[str, object]:
        if self.config_path.exists():
            self.config_path.unlink()
        return self.get_status()

    def get_status(self) -> dict[str, object]:
        if not self.config_path.exists():
            return {
                "provider": None,
                "model": None,
                "api_key_configured": False,
                "updated_at": None,
            }
        payload = self.load()
        return {
            "provider": payload.get("provider"),
            "model": payload.get("model"),
            "api_key_configured": bool(payload.get("api_key")),
            "updated_at": payload.get("updated_at"),
        }


def default_llm_config_service() -> LLMConfigService:
    return LLMConfigService(config_path=resolve_llm_config_path())
