from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
MATRIX_PATH = Path(__file__).with_name("capability-matrix.json")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def _is_tracked(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def test_capability_matrix_is_complete_and_all_required_items_are_supported():
    matrix = _load_matrix()
    capabilities = matrix["capabilities"]
    required_ids = {
        "consensus_layer",
        "candidate_layer",
        "alignment_layer",
        "mdwc_layer",
        "arbitration_layer",
        "memory_layer",
        "provider_registry",
        "local_provider_a_b",
        "cloud_provider_interface",
        "workflow_state_machine",
        "learning_mode",
        "self_iteration_mode",
        "meta_policy_agent",
        "human_confirmation_gate",
        "glossary",
        "special_mark",
        "user_correction_feedback",
        "rating_feedback",
        "history",
        "settings",
        "i18n",
        "api_key_safety",
    }

    seen_ids = {str(item["id"]) for item in capabilities}

    assert seen_ids == required_ids
    assert all(item["status"] == "supported" for item in capabilities)
    assert all(item["evidence_tests"] for item in capabilities)


def test_consensus_layer_candidate_alignment_mdwc_and_arbitration():
    from consensus_translation.agent_consensus import (
        align_translation_candidates,
        arbitrate_consensus_result,
        collect_consensus_candidates,
    )
    from consensus_translation.agent_contracts import TranslationCandidate
    from consensus_translation.mdwc import MDWCContext

    collected = collect_consensus_candidates(
        source_text="Leviathan wakes. Alice runs.",
        provider_candidates=[
            TranslationCandidate(
                provider_id="localProviderA",
                text="Liweitan wakes. Alice runs.",
                confidence=0.82,
                cost=0.0,
                latency=0.08,
                provider_kind="local",
                provider_role="local_a",
                reasoning="preserves glossary term",
            ),
            TranslationCandidate(
                provider_id="localProviderB",
                text="The giant wakes.",
                confidence=0.58,
                cost=0.0,
                latency=0.07,
                provider_kind="local",
                provider_role="local_b",
                reasoning="omits second segment",
            ),
        ],
        glossary_matches={"Leviathan": "Liweitan"},
        translation_memory_matches={"Leviathan wakes. Alice runs.": "Liweitan wakes. Alice runs."},
    )
    alignment = align_translation_candidates(
        source_text="Leviathan wakes. Alice runs.",
        candidates=collected.candidates,
        glossary_matches={"Leviathan": "Liweitan"},
    )
    decision = arbitrate_consensus_result(
        candidates=collected.candidates,
        alignment=alignment,
        mdwc_context=MDWCContext(
            topic_match_score=0.7,
            provider_historical_rating=0.8,
            topic_historical_rating=0.7,
            user_rating_signal=0.6,
        ),
    )

    first = collected.candidates[0]
    assert first.provider_id == "localProviderA"
    assert first.text
    assert first.confidence > 0
    assert first.reasoning
    assert first.cost == 0.0
    assert first.latency == 0.08
    assert any("terminology_conflict" in item.conflict_types for item in alignment.aligned_segments)
    assert "omission" in alignment.conflict_summary
    assert decision.final_score >= 0
    assert decision.confidence_level in {"low", "medium", "high"}
    assert decision.conflict_points
    assert decision.requires_human_review is True
    assert decision.arbitration_reason
    assert decision.accepted_segments
    assert decision.rejected_segments


def test_mdwc_dimensions_include_feedback_context_and_special_penalty():
    from consensus_translation.agent_contracts import TranslationCandidate
    from consensus_translation.mdwc import MDWCContext, evaluate_mdwc_consensus

    result = evaluate_mdwc_consensus(
        [
            TranslationCandidate(
                provider_id="localProviderA",
                text="Liweitan wakes.",
                confidence=0.83,
                provider_kind="local",
                term_hits={"terms": 2},
            ),
            TranslationCandidate(
                provider_id="cloudProviderA",
                text="Leviathan awakens.",
                confidence=0.76,
                provider_kind="cloud",
                is_mock=False,
            ),
        ],
        context=MDWCContext(
            topic_match_score=0.9,
            user_rating_signal=0.6,
            provider_historical_rating=0.7,
            special_marker_count=1,
            low_rating_penalty=0.1,
            mdwc_user_mismatch_rate=0.2,
        ),
    )

    dimensions = result.scoring_dimensions

    assert "providerReliability" in dimensions
    assert "terminology" in dimensions
    assert "context" in dimensions
    assert "userRatingSignal" in dimensions
    assert "conflictPenalty" in dimensions
    assert "specialRiskPenalty" in dimensions
    assert "special_marker_penalty" in result.conflicts
    assert result.requires_human_review is True


def test_provider_controls_keep_real_mock_and_cloud_boundaries():
    from consensus_translation.agent_contracts import AgentMode, TranslationCandidate
    from consensus_translation.agent_providers import StaticModelProvider
    from consensus_translation.agent_workflows import run_agent_translation

    local = StaticModelProvider("localProviderA", "local candidate", 0.74)
    cloud_providers = [
        StaticModelProvider(
            f"cloudProvider{i}",
            f"cloud candidate {i}",
            0.61,
            estimated_cost=0.01,
            requires_api=True,
        )
        for i in range(1, 5)
    ]

    result = run_agent_translation(
        text="Leviathan wakes.",
        source_lang="en",
        target_lang="zh",
        topic="myth",
        mode=AgentMode.AI_ASSISTED,
        providers=[local, *cloud_providers],
        api_enabled=True,
        budget_limit=1.0,
    )

    provider_ids = {candidate.provider_id for candidate in result.candidates}

    assert {"localProviderA", "cloudProvider1", "cloudProvider2", "cloudProvider3"}.issubset(provider_ids)
    assert "cloudProvider4" not in provider_ids
    assert "provider_skipped:cloudProvider4:cloud_provider_limit" in result.contract.trace
    assert all(not getattr(candidate, "is_mock", False) for candidate in result.candidates)
    assert TranslationCandidate(
        provider_id="mockProvider",
        text="mock",
        confidence=0.1,
        is_mock=True,
        provider_kind="mock",
    ).is_mock is True


def test_workflow_state_machine_records_human_gate_and_rating_event():
    from consensus_translation.agent_workflow_state import (
        WorkflowEvent,
        WorkflowState,
        WorkflowStateMachine,
    )

    machine = WorkflowStateMachine()
    states = [
        machine.apply(WorkflowEvent.START_TRANSLATION),
        machine.apply(WorkflowEvent.LOCAL_TRANSLATION_DONE),
        machine.apply(WorkflowEvent.CONSENSUS_DONE),
        machine.apply(WorkflowEvent.ARBITRATION_DONE),
    ]
    rating_state = machine.apply(WorkflowEvent.RATING_SUBMITTED)
    final_state = machine.apply(WorkflowEvent.USER_CONFIRMED)

    assert states == [
        WorkflowState.INPUT_READY,
        WorkflowState.LOCAL_TRANSLATING,
        WorkflowState.CONSENSUS_SCORING,
        WorkflowState.WAITING_HUMAN_CONFIRMATION,
    ]
    assert rating_state == WorkflowState.WAITING_HUMAN_CONFIRMATION
    assert final_state == WorkflowState.COMPLETED
    assert "workflow:waitingHumanConfirmation" in machine.trace_labels()


def test_local_mode_keeps_dual_provider_mdwc_and_human_gate(monkeypatch):
    from consensus_translation import workflows
    from consensus_translation.contracts import StageStatus

    class EngineA:
        def translate(self, _text: str, _source: str, _target: str):
            return "Liweitan wakes.", 0.62

    class EngineB:
        def translate(self, _text: str, _source: str, _target: str):
            return "The giant wakes.", 0.53

    monkeypatch.setattr(workflows, "LocalEngineA", EngineA)
    monkeypatch.setattr(workflows, "LocalEngineB", EngineB)

    result = workflows.run_local_job(
        "Leviathan wakes.",
        "en",
        "zh",
        "myth",
    )

    assert result["cand_a"] == "Liweitan wakes."
    assert result["cand_b"] == "The giant wakes."
    assert result["contract"]["stage_status"]["current"] == StageStatus.FINALIZE.value
    assert set(result["weights"]) == {"token", "sentence", "segment", "user_prior"}
    assert sum(float(value) for value in result["weights"].values()) == pytest.approx(1.0)
    assert result["final_score"] >= 0
    assert "decision_reason" in result
    assert "provisional_text" in result


def test_self_iteration_requires_validation_and_caps_at_three_rounds():
    from consensus_translation.agent_contracts import AgentMode, AgentRunStatus
    from consensus_translation.agent_evaluators import EvaluationResult
    from consensus_translation.agent_providers import StaticModelProvider
    from consensus_translation.agent_workflows import run_agent_translation

    class LowScoreEvaluator:
        evaluator_id = "low-score"
        requires_api = False
        estimated_cost = 0.0

        def evaluate(self, request):
            return EvaluationResult(
                evaluator_id=self.evaluator_id,
                score=0.2,
                metrics={"overall": 0.2},
                rationale=f"round={request.round_index}",
                cost=0.0,
            )

    with pytest.raises(ValueError, match="requires training_text and validation_text"):
        run_agent_translation(
            text="Leviathan wakes.",
            source_lang="en",
            target_lang="zh",
            topic="myth",
            mode=AgentMode.SELF_ITERATIVE,
            providers=[StaticModelProvider("localProviderA", "candidate", 0.8)],
            api_enabled=False,
            budget_limit=1.0,
        )

    result = run_agent_translation(
        text="Leviathan wakes.",
        source_lang="en",
        target_lang="zh",
        topic="myth",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[StaticModelProvider("localProviderA", "candidate", 0.8)],
        api_enabled=False,
        budget_limit=1.0,
        training_text="training sample",
        validation_text="validation sample",
        evaluator=LowScoreEvaluator(),
    )

    rounds = [item for item in result.contract.trace if item.startswith("round:")]

    assert rounds == ["round:1", "round:2", "round:3"]
    assert result.contract.status == AgentRunStatus.NEEDS_REVIEW
    assert "validation_failed:max_rounds" in result.contract.trace


def test_meta_policy_uses_rating_special_risk_budget_and_validation():
    from consensus_translation.agent_contracts import AgentMode
    from consensus_translation.agent_meta_policy import MetaPolicyAgent, MetaPolicyContext

    high_risk = MetaPolicyAgent().select_mode(
        training_text="alpha beta gamma",
        validation_text="one two three",
        api_enabled=True,
        budget_limit=5.0,
        context=MetaPolicyContext(
            topic_match_score=1.0,
            domain_tag_count=3,
            special_marker_count=2,
            user_correction_count=3,
            provider_average_rating=2.0,
            recent_low_rating_count=4,
            mdwc_user_mismatch_rate=0.7,
            rating_sample_count=8,
        ),
    )
    no_budget = MetaPolicyAgent().select_mode(
        training_text="alpha beta",
        validation_text="one two",
        api_enabled=True,
        budget_limit=0.0,
    )

    assert high_risk.selected_mode == AgentMode.LEARNING
    assert high_risk.requires_human_confirmation is True
    assert high_risk.max_iterations == 1
    assert high_risk.risk_level == "high"
    assert no_budget.selected_mode == AgentMode.LEARNING
    assert no_budget.fallback_plan == "stay_in_learning_mode_until_budget_is_available"


def test_rating_feedback_and_glossary_writeback_require_explicit_user_actions(tmp_path):
    from consensus_translation.agent_contracts import AgentMode, AgentRunStatus
    from consensus_translation.agent_feedback import TranslationRatingSubmission
    from consensus_translation.agent_providers import StaticModelProvider
    from consensus_translation.agent_store import AgentRunStore
    from consensus_translation.agent_workflows import run_agent_translation

    store = AgentRunStore(tmp_path / "agent.sqlite3")
    result = run_agent_translation(
        text="Leviathan wakes.",
        source_lang="en",
        target_lang="zh",
        topic="myth",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("localProviderA", "Liweitan wakes.", 0.72)],
        api_enabled=False,
        budget_limit=1.0,
        store=store,
    )

    pending = store.list_revision_events(confirmed=False, run_id=result.contract.run_id)

    assert result.contract.status == AgentRunStatus.AWAITING_HUMAN_CONFIRMATION
    assert pending
    assert store.export_topic("myth")["terms"] == {}
    assert store.skip_translation_rating(result.contract.run_id) is None
    assert store.list_translation_ratings() == []

    event_id = int(pending[0]["id"])
    assert store.mark_revision_event_special_by_id(event_id) is True
    assert store.confirm_revision_event_by_id(event_id) is True
    confirmed_terms = store.export_topic("myth")["terms"]
    confirmed_term_entries = store.export_topic_entries("myth")["terms"]

    assert confirmed_terms["Leviathan wakes."] == "Liweitan wakes."
    assert confirmed_term_entries[0]["source"] == "Leviathan wakes."
    assert confirmed_term_entries[0]["confirmed_by_user"] is True
    assert confirmed_term_entries[0]["is_special"] is True

    rating = store.record_translation_rating(
        TranslationRatingSubmission(
            task_id="task-1",
            workflow_run_id=result.contract.run_id,
            mode=result.contract.mode.value,
            source_language="en",
            target_language="zh",
            topic="myth",
            rating=2,
            issue_tags=("terminology_error",),
            mdwc_snapshot={"finalScore": 0.88},
            provider_snapshot=[{"providerId": "localProviderA"}],
            source_text="Leviathan wakes.",
            final_translation="Liweitan wakes.",
        )
    )
    summary = store.rating_signal_summary(
        topic="myth",
        source_language="en",
        target_language="zh",
        mode=result.contract.mode.value,
        provider_ids=("localProviderA",),
    )

    assert rating.rating == 2
    assert summary.sample_count == 1
    assert summary.low_rating_penalty > 0


def test_product_surface_languages_history_settings_and_api_key_safety():
    assert (ROOT / "app.py").exists()

    import app

    assert getattr(app, "LANGUAGE_OPTIONS", None) == ["zh", "en", "ja"]

    desktop_root = ROOT / "src" / "consensus_translation" / "desktop_qt"
    if _is_tracked(desktop_root / "application.py"):
        assert _is_tracked(desktop_root / "i18n_resources" / "zh-CN.json")
        assert _is_tracked(desktop_root / "i18n_resources" / "en-US.json")
        assert _is_tracked(desktop_root / "pages" / "history.py")
        assert _is_tracked(desktop_root / "pages" / "settings.py")

    provider_config = ROOT / "src" / "consensus_translation" / "agent_provider_config.py"
    credential_store = ROOT / "src" / "consensus_translation" / "agent_credentials.py"
    agent_store = ROOT / "src" / "consensus_translation" / "agent_store.py"
    if _is_tracked(provider_config):
        text = provider_config.read_text(encoding="utf-8")
        assert "credential_id" in text
        assert "credential_store.get_secret(config.credential_id)" in text
    if _is_tracked(credential_store):
        text = credential_store.read_text(encoding="utf-8")
        assert "CryptProtectData" in text or "_protect" in text
    if _is_tracked(agent_store):
        text = agent_store.read_text(encoding="utf-8")
        provider_config_schema = text[
            text.index("create table if not exists provider_configs") :
            text.index("create table if not exists agent_runs")
        ]
        assert "credential_id text not null" in provider_config_schema
        assert "api_key" not in provider_config_schema.lower()
