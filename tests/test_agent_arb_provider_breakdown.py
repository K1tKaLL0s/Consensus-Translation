from src.core.agents.agent_arb import select_consensus


def test_select_consensus_auto_approved_includes_provider_breakdown() -> None:
    candidates = [
        {"text": "候选A", "final": 0.89, "provider": "deepseek"},
        {"text": "候选B", "final": 0.95, "provider": "gemini"},
    ]

    result = select_consensus(
        candidates=candidates,
        threshold=0.92,
        kanji_raw="漢字原文",
        romaji="",
    )

    assert result["status"] == "auto_approved"
    assert result["winner"] == "候选B"
    assert result["provider_breakdown"] == {
        "attempted": ["deepseek", "gemini"],
        "winners_provider": "gemini",
    }
