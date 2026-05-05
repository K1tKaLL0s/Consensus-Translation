import asyncio

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

    state = asyncio.run(
        orchestrator.run(
            raw_text="機械翻訳の品質評価",
            source_declaration="human_declaration",
        )
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

    state = asyncio.run(MAATCSOrchestrator().run("原文", "declared-by-user"))

    assert state["source_declaration"] == "declared-by-user"


def test_run_uses_unknown_term_when_extractor_returns_empty(monkeypatch) -> None:
    from src.core import agent_orchestrator as orchestrator_module

    etym_called = False
    gen_called = False
    select_called = False

    monkeypatch.setattr(orchestrator_module, "extract_candidate_terms", lambda text: [])

    def fake_analyze_etymology(term: str, context: str, provider: str = "gemini") -> dict[str, str]:
        nonlocal etym_called
        etym_called = True
        return {"term": term, "analysis": "ok"}

    def fake_generate_candidates(term: str) -> dict[str, str]:
        nonlocal gen_called
        gen_called = True
        return {"gen_a": "A", "gen_b": "B", "gen_c": "C"}

    def fake_select_consensus(candidates, threshold, kanji_raw, romaji):
        nonlocal select_called
        select_called = True
        return {"status": "auto_approved", "winner": "should_not_happen", "final": 0.9}

    monkeypatch.setattr(orchestrator_module, "analyze_etymology", fake_analyze_etymology)
    monkeypatch.setattr(orchestrator_module, "generate_candidates", fake_generate_candidates)
    monkeypatch.setattr(orchestrator_module, "compute_final_score", lambda *args, **kwargs: 0.6)
    monkeypatch.setattr(orchestrator_module, "select_consensus", fake_select_consensus)

    state = asyncio.run(MAATCSOrchestrator().run("原文", "declared-by-user"))

    assert state["terms"] == ["unknown_term"]
    assert state["candidate_pool"] == []
    assert state["consensus"]["status"] == "fallback"
    assert state["consensus"]["winner"] == "unknown_term"
    assert not etym_called
    assert not gen_called
    assert not select_called


def test_run_reuses_compiled_graph_across_invocations(monkeypatch) -> None:
    from src.core import agent_orchestrator as orchestrator_module

    build_call_count = 0
    app_ids: list[int] = []

    class FakeApp:
        async def ainvoke(self, state):
            app_ids.append(id(self))
            return {
                **state,
                "terms": ["術語"],
                "etym_reports": [],
                "candidate_pool": [],
                "consensus": {"status": "fallback", "winner": "術語", "final": 0.0},
            }

    def fake_build_graph(self):
        nonlocal build_call_count
        build_call_count += 1
        return FakeApp()

    monkeypatch.setattr(orchestrator_module.MAATCSOrchestrator, "_build_graph", fake_build_graph)

    orchestrator = MAATCSOrchestrator()
    state1 = asyncio.run(orchestrator.run("原文1", "declared-by-user"))
    state2 = asyncio.run(orchestrator.run("原文2", "declared-by-user"))

    assert state1["consensus"]["status"] == "fallback"
    assert state2["consensus"]["status"] == "fallback"
    assert build_call_count == 1
    assert len(app_ids) == 2
    assert app_ids[0] == app_ids[1]
