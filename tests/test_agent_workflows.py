from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_contracts import (
    AgentMode,
    AgentRunStatus,
    TranslationCandidate,
)
from consensus_translation.agent_evaluators import EvaluationResult
from consensus_translation.agent_inputs import AgentInputDocument
from consensus_translation.agent_providers import LocalWorkflowProvider, StaticModelProvider
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.agent_workflows import run_agent_batch_translation, run_agent_translation


class CapturingLexiconProvider:
    provider_id = "capture-lexicon"
    requires_api = False
    estimated_cost = 0.0

    def __init__(self):
        self.requests = []

    def translate(self, request):
        self.requests.append(request)
        target = request.lexicon_terms["Leviathan"]
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=f"use memory:{target}",
            confidence=0.8,
            term_hits={"terms": len(request.lexicon_terms)},
        )


class RoundAwareProvider:
    provider_id = "round-aware"
    requires_api = False
    estimated_cost = 0.0

    def __init__(self, outputs):
        self.outputs = outputs
        self.calls = 0

    def translate(self, request):
        self.calls += 1
        text, confidence = self.outputs[request.round_index - 1]
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=text,
            confidence=confidence,
        )


class ScriptedEvaluator:
    evaluator_id = "scripted-evaluator"
    requires_api = False
    estimated_cost = 0.0

    def __init__(self, scores):
        self.scores = scores
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        score = self.scores[request.round_index - 1]
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=score,
            metrics={"overall": score},
            rationale=f"scripted:{score}",
        )


class CapturingRemoteTrainingProvider:
    provider_id = "remote-training"
    requires_api = True
    estimated_cost = 0.0

    def __init__(self):
        self.requests = []

    def translate(self, request):
        self.requests.append(request)
        return TranslationCandidate(
            provider_id=self.provider_id,
            text="translated",
            confidence=0.8,
        )


def test_agent_translation_passes_matching_sqlite_lexicon_entries_to_provider(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    store.upsert_lexicon_entry("western_myth", "terms", "Leviathan", "Liweitan")
    store.upsert_lexicon_entry("western_myth", "phrases", "fallen angel", "duoluo tianshi")
    store.upsert_lexicon_entry("western_myth", "style_rules", "dialogue", "keep terse")
    provider = CapturingLexiconProvider()

    result = run_agent_translation(
        text="Leviathan meets a fallen angel in dialogue.",
        source_lang="en",
        target_lang="zh",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[provider],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
        lexicon_store=store,
    )

    request = provider.requests[0]
    assert request.lexicon_terms == {"Leviathan": "Liweitan"}
    assert request.lexicon_phrases == {"fallen angel": "duoluo tianshi"}
    assert request.style_rules == {"dialogue": "keep terse"}
    assert result.decision.final_text == "use memory:Liweitan"
    assert "lexicon_hits:terms=1,phrases=1,style_rules=1" in result.contract.trace


def test_learning_mode_generates_candidates_but_requires_human_confirmed_writeback():
    result = run_agent_translation(
        text="我が名はレヴィアタン",
        source_lang="ja",
        target_lang="zh",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[
            StaticModelProvider("local-a", "我的名字是利维坦", confidence=0.62),
            StaticModelProvider("local-b", "吾名利维坦", confidence=0.74),
        ],
        api_enabled=False,
        budget_limit=0.0,
    )

    assert result.contract.mode == AgentMode.LEARNING
    assert result.contract.status == AgentRunStatus.AWAITING_HUMAN_CONFIRMATION
    assert [candidate.provider_id for candidate in result.candidates] == [
        "local-a",
        "local-b",
    ]
    assert result.decision.final_text == "吾名利维坦"
    assert result.decision.vote_map == {"local-a": 1, "local-b": 1}
    assert result.lexicon_proposals
    assert all(proposal.requires_user_confirm for proposal in result.lexicon_proposals)
    assert "human_gate:required" in result.contract.trace


def test_remote_provider_receives_training_text_only_after_explicit_permission():
    blocked_provider = CapturingRemoteTrainingProvider()
    allowed_provider = CapturingRemoteTrainingProvider()

    run_agent_translation(
        text="source",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[blocked_provider],
        api_enabled=True,
        budget_limit=0.0,
        training_text="private training",
        allow_training_upload=False,
    )
    run_agent_translation(
        text="source",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[allowed_provider],
        api_enabled=True,
        budget_limit=0.0,
        training_text="approved training",
        allow_training_upload=True,
    )

    assert blocked_provider.requests[0].training_text is None
    assert allowed_provider.requests[0].training_text == "approved training"


def test_api_disabled_skips_remote_providers_and_uses_local_candidate():
    remote = StaticModelProvider(
        "remote-gpt",
        "remote candidate",
        confidence=0.99,
        requires_api=True,
    )
    local = StaticModelProvider("local-a", "local candidate", confidence=0.51)

    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[remote, local],
        api_enabled=False,
        budget_limit=0.0,
    )

    assert [candidate.provider_id for candidate in result.candidates] == ["local-a"]
    assert result.decision.final_text == "local candidate"
    assert "provider_skipped:remote-gpt:api_disabled" in result.contract.trace


def test_self_iterative_mode_requires_training_and_validation_sets():
    with pytest.raises(ValueError, match="training_text and validation_text"):
        run_agent_translation(
            text="hello",
            source_lang="en",
            target_lang="zh",
            topic="general",
            mode=AgentMode.SELF_ITERATIVE,
            providers=[StaticModelProvider("local-a", "你好", confidence=0.8)],
            api_enabled=False,
            budget_limit=1.0,
        )


def test_self_iterative_mode_uses_validation_score_to_continue_past_high_confidence():
    provider = RoundAwareProvider(
        [
            ("wrong output", 0.95),
            ("gold target", 0.99),
            ("unused", 0.99),
        ]
    )

    result = run_agent_translation(
        text="source text",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[provider],
        training_text="source text",
        validation_text="gold target",
        api_enabled=False,
        budget_limit=0.0,
    )

    assert provider.calls == 2
    assert result.contract.status == AgentRunStatus.FINALIZED
    assert result.decision.final_text == "gold target"
    assert "validation_passed:round=2" in result.contract.trace
    assert any(item.startswith("validation_score:round=1") for item in result.contract.trace)


def test_self_iterative_mode_accepts_custom_evaluator_for_validation_scoring():
    provider = RoundAwareProvider(
        [
            ("first output", 0.95),
            ("second output", 0.99),
            ("unused", 0.99),
        ]
    )
    evaluator = ScriptedEvaluator([0.2, 0.91, 0.1])

    result = run_agent_translation(
        text="source text",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[provider],
        training_text="source text",
        validation_text="gold target",
        api_enabled=False,
        budget_limit=0.0,
        evaluator=evaluator,
    )

    assert provider.calls == 2
    assert [request.candidate_text for request in evaluator.requests] == [
        "first output",
        "second output",
    ]
    assert result.contract.status == AgentRunStatus.FINALIZED
    assert "validation_evaluator:scripted-evaluator" in result.contract.trace
    assert "validation_score:round=2:overall=0.910000" in result.contract.trace


def test_self_iterative_mode_needs_review_after_validation_fails_all_rounds():
    provider = RoundAwareProvider(
        [
            ("wrong one", 0.81),
            ("wrong two", 0.82),
            ("wrong three", 0.83),
        ]
    )

    result = run_agent_translation(
        text="source text",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[provider],
        training_text="source text",
        validation_text="gold target",
        api_enabled=False,
        budget_limit=0.0,
    )

    assert provider.calls == 3
    assert result.contract.status == AgentRunStatus.NEEDS_REVIEW
    assert "validation_failed:max_rounds" in result.contract.trace


def test_budget_limit_stops_before_expensive_provider_call():
    expensive = StaticModelProvider(
        "remote-gpt",
        "expensive",
        confidence=0.9,
        estimated_cost=0.75,
        requires_api=True,
    )

    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[expensive],
        training_text="hello",
        validation_text="你好",
        api_enabled=True,
        budget_limit=0.5,
    )

    assert result.contract.status == AgentRunStatus.BUDGET_EXCEEDED
    assert result.candidates == []
    assert expensive.calls == 0
    assert "budget_exceeded:remote-gpt" in result.contract.trace


def test_self_decision_selects_iterative_when_validation_and_budget_are_available():
    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_DECISION,
        providers=[StaticModelProvider("remote-a", "你好", confidence=0.86)],
        training_text="hello",
        validation_text="你好",
        api_enabled=True,
        budget_limit=2.0,
    )

    assert result.contract.mode == AgentMode.SELF_DECISION
    assert result.contract.status == AgentRunStatus.FINALIZED
    assert "meta_policy:selected_mode=self_iterative" in result.contract.trace
    assert any(item.startswith("round:1") for item in result.contract.trace)


def test_self_decision_falls_back_to_learning_when_validation_coverage_is_too_low():
    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_DECISION,
        providers=[StaticModelProvider("local-a", "nihao", confidence=0.86)],
        training_text="alpha beta gamma delta",
        validation_text="x",
        api_enabled=True,
        budget_limit=2.0,
    )

    assert result.contract.status == AgentRunStatus.AWAITING_HUMAN_CONFIRMATION
    assert "meta_policy:selected_mode=learning" in result.contract.trace
    assert "meta_policy:reason=validation_coverage_low" in result.contract.trace


def test_batch_translation_preserves_each_input_reference():
    results = run_agent_batch_translation(
        documents=[
            AgentInputDocument(input_ref="a.txt", text="first"),
            AgentInputDocument(input_ref="b.md", text="second"),
        ],
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "译文", confidence=0.7)],
        api_enabled=False,
        budget_limit=0.0,
    )

    assert [result.contract.input_refs for result in results] == [["a.txt"], ["b.md"]]
    assert [result.decision.final_text for result in results] == ["译文", "译文"]


def test_local_workflow_provider_wraps_existing_local_job_contract():
    def fake_local_job(text, source_lang, target_lang, topic):
        assert text == "hello"
        assert source_lang == "en"
        assert target_lang == "zh"
        assert topic == "general"
        return {
            "final_text": "你好",
            "final_score": 0.66,
            "domain_hits": {"myth": 0, "history": 0, "science": 0},
            "needs_review": False,
        }

    provider = LocalWorkflowProvider(run_local_job_fn=fake_local_job)
    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[provider],
        api_enabled=False,
        budget_limit=0.0,
    )

    assert provider.requires_api is False
    assert result.candidates[0].provider_id == "local-workflow"
    assert result.candidates[0].text == "你好"
    assert result.candidates[0].confidence == 0.66
    assert result.candidates[0].term_hits == {"myth": 0, "history": 0, "science": 0}
