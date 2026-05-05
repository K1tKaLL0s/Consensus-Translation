from src.core.agent_orchestrator import MAATCSOrchestrator


def test_run_builds_state_with_consensus(monkeypatch) -> None:
    from src.core import agent_orchestrator as orchestrator_module

    call_order: list[str] = []

    def fake_extract_candidate_terms(text: str) -> list[str]:
        call_order.append("extract")
        assert text == "機械翻訳の品質評価"
        return ["品質評価"]

    def fake_analyze_etymology(
        term: str,
        context: str,
        provider: str = "gemini",
    ) -> dict[str, str]:
        call_order.append("etym")
        assert term == "品質評価"
        assert context == "機械翻訳の品質評価"
        assert provider == "gemini"
        return {"term": term, "analysis": "mock"}

    def fake_generate_candidates(term: str) -> dict[str, str]:
        call_order.append("gen")
        assert term == "品質評価"
        return {"gen_a": "A", "gen_b": "B", "gen_c": "C"}

    def fake_compute_final_score(
        mqm_score: float,
        context_score: float,
        frequency_score: float,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2,
    ) -> float:
        call_order.append("compute")
        return (mqm_score * alpha) + (context_score * beta) + (frequency_score * gamma)

    def fake_select_consensus(
        candidates: list[dict],
        threshold: float,
        kanji_raw: str,
        romaji: str,
    ) -> dict[str, str | float]:
        call_order.append("select")
        assert kanji_raw == "機械翻訳の品質評価"
        assert romaji == ""
        assert threshold == 0.9
        assert len(candidates) == 3
        return {"status": "auto_approved", "winner": "B", "final": 0.91}

    monkeypatch.setattr(
        orchestrator_module,
        "extract_candidate_terms",
        fake_extract_candidate_terms,
    )
    monkeypatch.setattr(orchestrator_module, "analyze_etymology", fake_analyze_etymology)
    monkeypatch.setattr(orchestrator_module, "generate_candidates", fake_generate_candidates)
    monkeypatch.setattr(orchestrator_module, "compute_final_score", fake_compute_final_score)
    monkeypatch.setattr(orchestrator_module, "select_consensus", fake_select_consensus)

    orchestrator = MAATCSOrchestrator()

    state = orchestrator.run(
        raw_text="機械翻訳の品質評価",
        source_declaration="human_declaration",
    )

    assert "consensus" in state
    assert state["consensus"]["winner"] == "B"
    assert call_order == ["extract", "etym", "gen", "compute", "compute", "compute", "select"]


def test_run_passthrough_source_declaration(monkeypatch) -> None:
    from src.core import agent_orchestrator as orchestrator_module

    monkeypatch.setattr(orchestrator_module, "extract_candidate_terms", lambda text: ["術語"])
    monkeypatch.setattr(
        orchestrator_module,
        "analyze_etymology",
        lambda term, context, provider="gemini": {"term": term, "analysis": "ok"},
    )
    monkeypatch.setattr(
        orchestrator_module,
        "generate_candidates",
        lambda term: {"gen_a": "A", "gen_b": "B", "gen_c": "C"},
    )
    monkeypatch.setattr(orchestrator_module, "compute_final_score", lambda *args, **kwargs: 0.5)
    monkeypatch.setattr(
        orchestrator_module,
        "select_consensus",
        lambda candidates, threshold, kanji_raw, romaji: {
            "status": "fallback",
            "winner": kanji_raw,
            "final": 0.5,
        },
    )

    state = MAATCSOrchestrator().run("原文", "declared-by-user")

    assert state["source_declaration"] == "declared-by-user"
