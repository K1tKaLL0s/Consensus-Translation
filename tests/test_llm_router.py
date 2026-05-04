import pytest

from src.core.llm_router import LLMRouter


def test_unknown_provider_raises_value_error() -> None:
    router = LLMRouter()

    with pytest.raises(ValueError):
        router.resolve_provider("unknown")


def test_generate_without_key_returns_mock_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    router = LLMRouter()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = router.generate("gpt", "hello")

    assert result == "[MOCK:gpt] hello"


@pytest.mark.parametrize(
    "provider",
    ["gpt", "qwen", "kimi", "deepseek", "gemini", "watsonx"],
)
def test_resolve_provider_accepts_supported_values(provider: str) -> None:
    router = LLMRouter()

    assert router.resolve_provider(provider) == provider
