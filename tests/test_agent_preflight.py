from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_context import ContextBudget
from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_preflight import build_remote_call_preflight
from consensus_translation.agent_providers import StaticModelProvider


class RemoteEvaluator:
    evaluator_id = "llm-judge"
    requires_api = True
    estimated_cost = 0.1


def test_remote_call_preflight_lists_remote_provider_calls_by_context_task():
    remote = StaticModelProvider(
        "remote-a",
        "translated",
        confidence=0.8,
        estimated_cost=0.2,
        requires_api=True,
    )
    local = StaticModelProvider("local-a", "local", confidence=0.6)

    preflight = build_remote_call_preflight(
        text="alpha beta\n\ngamma delta\n\nomega zeta",
        mode=AgentMode.LEARNING,
        providers=[remote, local],
        context_budget=ContextBudget(max_context_tokens=7, reserved_output_tokens=2),
        api_enabled=True,
        budget_limit=1.0,
    )

    assert preflight.requires_confirmation is True
    assert preflight.available_input_tokens == 5
    assert preflight.estimated_input_tokens == 6
    assert preflight.total_estimated_cost == 0.4
    assert [
        (call.provider_id, call.input_ref, call.estimated_input_tokens)
        for call in preflight.calls
    ] == [
        ("remote-a", "context-initial", 4),
        ("remote-a", "context-slice:2", 2),
    ]
    assert preflight.calls[0].text_preview == "alpha beta\n\ngamma delta"


def test_remote_call_preflight_marks_budget_excess_before_execution():
    remote = StaticModelProvider(
        "remote-a",
        "translated",
        confidence=0.8,
        estimated_cost=0.75,
        requires_api=True,
    )

    preflight = build_remote_call_preflight(
        text="alpha beta",
        mode=AgentMode.LEARNING,
        providers=[remote],
        context_budget=ContextBudget(max_context_tokens=64, reserved_output_tokens=8),
        api_enabled=True,
        budget_limit=0.5,
    )

    assert preflight.requires_confirmation is True
    assert preflight.total_estimated_cost == 0.75
    assert preflight.budget_exceeded is True
    assert preflight.warnings == ["budget_exceeded:estimated_remote_cost"]


def test_remote_call_preflight_includes_remote_validation_evaluator_calls():
    preflight = build_remote_call_preflight(
        text="alpha beta",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[StaticModelProvider("local-a", "local", confidence=0.6)],
        context_budget=ContextBudget(max_context_tokens=64, reserved_output_tokens=8),
        api_enabled=True,
        budget_limit=1.0,
        evaluator=RemoteEvaluator(),
        validation_text="reference target",
    )

    assert preflight.requires_confirmation is True
    assert preflight.total_estimated_cost == 0.3
    assert [
        (
            call.provider_id,
            call.input_ref,
            call.round_index,
            call.estimated_cost,
            call.data_scopes,
        )
        for call in preflight.calls
    ] == [
        ("evaluator:llm-judge", "context-initial", 1, 0.1, ("source", "candidate", "validation")),
        ("evaluator:llm-judge", "context-initial", 2, 0.1, ("source", "candidate", "validation")),
        ("evaluator:llm-judge", "context-initial", 3, 0.1, ("source", "candidate", "validation")),
    ]


def test_remote_preflight_requires_explicit_training_upload_permission():
    remote = StaticModelProvider(
        "remote-a",
        "translated",
        confidence=0.8,
        requires_api=True,
    )

    blocked = build_remote_call_preflight(
        text="alpha beta",
        mode=AgentMode.LEARNING,
        providers=[remote],
        context_budget=ContextBudget(max_context_tokens=64, reserved_output_tokens=8),
        api_enabled=True,
        budget_limit=1.0,
        training_text="approved style example",
        allow_training_upload=False,
    )
    allowed = build_remote_call_preflight(
        text="alpha beta",
        mode=AgentMode.LEARNING,
        providers=[remote],
        context_budget=ContextBudget(max_context_tokens=64, reserved_output_tokens=8),
        api_enabled=True,
        budget_limit=1.0,
        training_text="approved style example",
        allow_training_upload=True,
    )

    assert blocked.calls[0].data_scopes == ("source",)
    assert blocked.calls[0].estimated_input_tokens == 2
    assert "training_upload_disabled" in blocked.warnings
    assert allowed.calls[0].data_scopes == ("source", "training")
    assert allowed.calls[0].estimated_input_tokens == 5
    assert "training_upload_disabled" not in allowed.warnings
