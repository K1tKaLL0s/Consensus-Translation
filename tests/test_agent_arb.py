import pytest

from src.core.agents.agent_arb import compute_final_score, select_consensus


def test_compute_final_score_uses_weighted_formula() -> None:
    result = compute_final_score(0.8, 0.9, 0.6)
    expected = (0.8 * 0.5) + (0.9 * 0.3) + (0.6 * 0.2)
    assert result == pytest.approx(expected)


def test_select_consensus_falls_back_below_threshold() -> None:
    candidates = [
        {"text": "候选A", "final": 0.80},
        {"text": "候选B", "final": 0.88},
    ]

    result = select_consensus(
        candidates=candidates,
        threshold=0.90,
        kanji_raw="漢字原文",
        romaji="kanji genbun",
    )

    assert result["status"] == "fallback"
    assert result["winner"] == "kanji genbun"


def test_select_consensus_auto_approves_above_threshold() -> None:
    candidates = [
        {"text": "候选A", "final": 0.89},
        {"text": "候选B", "final": 0.95},
    ]

    result = select_consensus(
        candidates=candidates,
        threshold=0.92,
        kanji_raw="漢字原文",
        romaji="",
    )

    assert result["status"] == "auto_approved"
    assert result["winner"] == "候选B"
