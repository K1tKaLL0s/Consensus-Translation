from src.core.agents.agent_gen import generate_candidates
from src.core.agents.agent_etym import analyze_etymology
from src.core.agents.agent_tex import extract_candidate_terms


def test_extract_candidate_terms_returns_non_empty_list_for_repeated_japanese_text() -> None:
    text = "機械翻訳の品質評価は重要です。機械翻訳の品質評価は重要です。機械翻訳の品質評価は重要です。"

    terms = extract_candidate_terms(text)

    assert isinstance(terms, list)
    assert terms
    assert all(isinstance(term, str) and term for term in terms)


def test_generate_candidates_returns_three_paths() -> None:
    result = generate_candidates("品質評価")

    assert set(result.keys()) == {"gen_a", "gen_b", "gen_c"}


def test_generate_candidates_uses_router_mocked_three_providers(
    monkeypatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("WATSONX_API_KEY", raising=False)
    monkeypatch.delenv("MAATCS_ALLOW_MOCK_FALLBACK", raising=False)

    result = generate_candidates("品質評価")

    assert "[MOCK:deepseek]" in result["gen_a"]
    assert "[MOCK:gemini]" in result["gen_b"]
    assert "[MOCK:watsonx]" in result["gen_c"]


def test_analyze_etymology_returns_term_and_analysis_with_consistent_context_snippet(
    monkeypatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("MAATCS_ALLOW_MOCK_FALLBACK", raising=False)
    context = "a" * 250

    result = analyze_etymology(term="品質評価", context=context, provider="gemini")

    assert result["term"] == "品質評価"
    assert "analysis" in result
    assert "[MOCK:gemini]" in result["analysis"]
    assert result["context"] == context[:200]
