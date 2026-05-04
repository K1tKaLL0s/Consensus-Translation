import pytest

from src.core.llm_router import LLMRouter


def test_unknown_provider_raises_value_error() -> None:
    router = LLMRouter()

    with pytest.raises(ValueError):
        router.resolve_provider("unknown")


def test_generate_without_key_returns_mock_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    router = LLMRouter()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MAATCS_ALLOW_MOCK_FALLBACK", raising=False)

    result = router.generate("gpt", "hello")

    assert result == "[MOCK:gpt] hello"


def test_generate_with_key_returns_real_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    router = LLMRouter()
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    monkeypatch.delenv("MAATCS_ALLOW_MOCK_FALLBACK", raising=False)

    result = router.generate("gpt", "hello")

    assert result == "[REAL:gpt] hello"


def test_generate_without_key_raises_when_mock_fallback_disallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = LLMRouter(allow_mock_fallback=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        router.generate("gpt", "hello")


def test_generate_without_key_raises_when_env_disables_mock_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAATCS_ALLOW_MOCK_FALLBACK", "false")
    router = LLMRouter()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        router.generate("gpt", "hello")


@pytest.mark.parametrize(
    "provider",
    ["gpt", "qwen", "kimi", "deepseek", "gemini", "watsonx"],
)
def test_resolve_provider_accepts_supported_values(provider: str) -> None:
    router = LLMRouter()

    assert router.resolve_provider(provider) == provider
