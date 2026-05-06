import pytest

from src.core.agents import agent_gen


def test_generate_candidates_returns_provider_metadata_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRouter:
        def generate(self, provider: str, prompt: str) -> str:
            return f"{provider}::{prompt}"

    monkeypatch.setattr(agent_gen, "LLMRouter", lambda: FakeRouter())

    result = agent_gen.generate_candidates("品質評価", providers=["deepseek", "gemini"])

    assert set(result.keys()) == {"deepseek", "gemini"}
    assert result["deepseek"]["provider"] == "deepseek"
    assert result["deepseek"]["text"].startswith("deepseek::")
    assert isinstance(result["deepseek"]["latency_ms"], float)
    assert result["deepseek"]["latency_ms"] >= 0.0
    assert result["deepseek"]["error"] is None

    assert result["gemini"]["provider"] == "gemini"
    assert result["gemini"]["text"].startswith("gemini::")
    assert isinstance(result["gemini"]["latency_ms"], float)
    assert result["gemini"]["latency_ms"] >= 0.0
    assert result["gemini"]["error"] is None
