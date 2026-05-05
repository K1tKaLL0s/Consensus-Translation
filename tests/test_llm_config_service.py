from pathlib import Path

import pytest

from src.services.llm_config_service import LLMConfigService


def test_save_and_load_llm_config_roundtrip(tmp_path: Path) -> None:
    service = LLMConfigService(config_path=tmp_path / "llm_config.json")

    status = service.save(provider="gemini", model="gemini-2.5-pro", api_key="secret")

    payload = service.load()
    assert payload["provider"] == "gemini"
    assert payload["model"] == "gemini-2.5-pro"
    assert payload["api_key"] == "secret"
    assert status["api_key_configured"] is True


def test_status_redacts_secret(tmp_path: Path) -> None:
    service = LLMConfigService(config_path=tmp_path / "llm_config.json")
    service.save(provider="deepseek", model="deepseek-chat", api_key="abc123")

    status = service.get_status()

    assert status["provider"] == "deepseek"
    assert status["model"] == "deepseek-chat"
    assert status["api_key_configured"] is True
    assert "api_key" not in status


def test_clear_resets_status(tmp_path: Path) -> None:
    service = LLMConfigService(config_path=tmp_path / "llm_config.json")
    service.save(provider="qwen", model="qwen-plus", api_key="secret")

    status = service.clear()

    assert status["provider"] is None
    assert status["model"] is None
    assert status["api_key_configured"] is False


def test_save_rejects_unsupported_provider(tmp_path: Path) -> None:
    service = LLMConfigService(config_path=tmp_path / "llm_config.json")

    with pytest.raises(ValueError, match="unsupported provider"):
        service.save(provider="foo", model="bar", api_key="baz")
