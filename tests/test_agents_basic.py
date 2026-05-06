import re

import pytest

from src.core.agents.agent_gen import generate_candidates
from src.core.agents.agent_etym import analyze_etymology
from src.core.agents.agent_tex import extract_candidate_terms


def test_extract_candidate_terms_returns_non_empty_list_for_repeated_japanese_text() -> None:
    text = "機械翻訳の品質評価は重要です。機械翻訳の品質評価は重要です。機械翻訳の品質評価は重要です。"

    terms = extract_candidate_terms(text)

    assert isinstance(terms, list)
    assert terms
    assert all(isinstance(term, str) and term for term in terms)


def test_extract_candidate_terms_do_not_include_whitespace_tokens() -> None:
    text = "機械翻訳 の 品質 評価 は 重要 です。機械翻訳 の 品質 評価 は 重要 です。"

    terms = extract_candidate_terms(text)

    assert terms
    assert all(not re.search(r"\s", term) for term in terms)


def test_extract_candidate_terms_japanese_no_space_text_avoids_full_sentence_term() -> None:
    sentence = "機械翻訳の品質評価は重要です"
    text = f"{sentence}。{sentence}。{sentence}。"

    terms = extract_candidate_terms(text)

    assert terms
    assert sentence not in terms


def test_extract_candidate_terms_limit_japanese_term_length_range() -> None:
    text = "機械翻訳の品質評価は重要です。機械翻訳の品質評価は重要です。機械翻訳の品質評価は重要です。"

    terms = extract_candidate_terms(text)

    assert terms
    assert all(2 <= len(term) <= 12 for term in terms)


def test_generate_candidates_returns_three_paths() -> None:
    result = generate_candidates("品質評価")

    assert set(result.keys()) == {"deepseek", "gemini", "watsonx"}


def test_generate_candidates_uses_router_mocked_three_providers(
    monkeypatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("WATSONX_API_KEY", raising=False)
    monkeypatch.delenv("MAATCS_ALLOW_MOCK_FALLBACK", raising=False)

    result = generate_candidates("品質評価")

    assert "[MOCK:deepseek]" in result["deepseek"]["text"]
    assert "[MOCK:gemini]" in result["gemini"]["text"]
    assert "[MOCK:watsonx]" in result["watsonx"]["text"]


def test_generate_candidates_raises_value_error_for_blank_term() -> None:
    with pytest.raises(ValueError):
        generate_candidates("   ")


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


def test_analyze_etymology_raises_value_error_for_blank_term() -> None:
    with pytest.raises(ValueError):
        analyze_etymology(term="\n\t ", context="any", provider="gemini")
