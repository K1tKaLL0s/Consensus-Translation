from src.core.agents.agent_gen import generate_candidates
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
