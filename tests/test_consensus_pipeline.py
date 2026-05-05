import pytest

from src.core.agent_orchestrator import MAATCSOrchestrator


@pytest.mark.asyncio
async def test_consensus_pipeline_end_to_end_preserves_source_declaration() -> None:
    raw_text = (
        "游戏王カードゲームの新規カードは召喚条件が厳しいが、"
        "デッキ構築の自由度が高くて面白い。"
    )

    orchestrator = MAATCSOrchestrator()
    state = await orchestrator.run(
        raw_text=raw_text,
        source_declaration="游戏王卡牌游戏",
    )

    assert len(state["terms"]) >= 1
    consensus = state["consensus"]
    assert isinstance(consensus, dict)
    assert "status" in consensus
    assert "winner" in consensus
    assert consensus["status"] in {"auto_approved", "fallback"}
    assert state["source_declaration"] == "游戏王卡牌游戏"
