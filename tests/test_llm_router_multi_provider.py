import pytest

from src.core.llm_router import LLMRouter


def test_generate_dispatch_returns_adapter_text_when_has_key_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = LLMRouter()

    monkeypatch.setattr(router, "_get_api_key", lambda provider: "secret")

    result = router.generate("deepseek", "hello")

    assert result == "[REAL:deepseek] hello"


def test_generate_falls_back_to_mock_when_adapter_fails_and_mock_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = LLMRouter(allow_mock_fallback=True)

    monkeypatch.setattr(router, "_get_api_key", lambda provider: "secret")

    def _boom(provider: str, prompt: str, api_key: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(router, "_dispatch_provider", _boom)

    result = router.generate("gemini", "hello")

    assert result == "[MOCK:gemini] hello"


def test_generate_raises_when_adapter_fails_and_mock_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = LLMRouter(allow_mock_fallback=False)

    monkeypatch.setattr(router, "_get_api_key", lambda provider: "secret")

    def _boom(provider: str, prompt: str, api_key: str) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(router, "_dispatch_provider", _boom)

    with pytest.raises(RuntimeError, match="boom"):
        router.generate("watsonx", "hello")


def test_generate_raises_env_error_and_skips_dispatch_when_key_missing_and_mock_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = LLMRouter(allow_mock_fallback=False)

    monkeypatch.setattr(router, "_get_api_key", lambda provider: None)

    called = {"dispatch": False}

    def _dispatch(provider: str, prompt: str, api_key: str) -> str:
        called["dispatch"] = True
        return "unreachable"

    monkeypatch.setattr(router, "_dispatch_provider", _dispatch)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        router.generate("gpt", "hello")

    assert called["dispatch"] is False
