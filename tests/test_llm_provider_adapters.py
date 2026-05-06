import pytest

from src.core.providers.deepseek_adapter import DeepSeekAdapter
from src.core.providers.gemini_adapter import GeminiAdapter
from src.core.providers.watsonx_adapter import WatsonXAdapter


@pytest.mark.parametrize(
    ("adapter", "provider"),
    [
        (DeepSeekAdapter(), "deepseek"),
        (GeminiAdapter(), "gemini"),
        (WatsonXAdapter(), "watsonx"),
    ],
)
def test_adapter_generate_returns_real_text_when_api_key_present(adapter, provider: str) -> None:
    result = adapter.generate(prompt="hello", api_key="secret")

    assert result == f"[REAL:{provider}] hello"


@pytest.mark.parametrize(
    "adapter",
    [DeepSeekAdapter(), GeminiAdapter(), WatsonXAdapter()],
)
def test_adapter_generate_raises_when_api_key_missing(adapter) -> None:
    with pytest.raises(ValueError, match="api_key"):
        adapter.generate(prompt="hello", api_key="")
