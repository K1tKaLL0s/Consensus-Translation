import asyncio

from src.core.agent_orchestrator import MAATCSOrchestrator


def test_consensus_pipeline_end_to_end_preserves_source_declaration() -> None:
    raw_text = (
        "游戏王カードゲームの新規カードは召喚条件が厳しいが、"
        "デッキ構築の自由度が高くて面白い。"
    )

    state = asyncio.run(
        MAATCSOrchestrator().run(
            raw_text=raw_text,
            source_declaration="游戏王卡牌游戏",
        )
    )

    assert len(state["terms"]) >= 1
    assert "consensus" in state
    assert state["source_declaration"] == "游戏王卡牌游戏"
