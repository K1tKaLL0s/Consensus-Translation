from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_context import (
    ContextBudget,
    estimate_context_tokens,
    plan_context_slices,
)


def test_estimate_context_tokens_counts_cjk_and_ascii_predictably():
    assert estimate_context_tokens("命运之轮") == 4
    assert estimate_context_tokens("fate wheel turns") == 3
    assert estimate_context_tokens("命运 wheel") == 3


def test_plan_context_slices_splits_into_workflow_and_pending_parts():
    text = "第一段命运之轮转动。\n\n第二段利维坦苏醒。\n\n第三段世界线偏移。"
    budget = ContextBudget(max_context_tokens=18, reserved_output_tokens=5)

    plan = plan_context_slices(text, budget)

    assert plan.estimated_input_tokens == estimate_context_tokens(text)
    assert plan.available_input_tokens == 13
    assert len(plan.slices) == 3
    assert plan.slices[0].text == "第一段命运之轮转动。"
    assert plan.slices[0].fits_current_task is True
    assert plan.slices[1].fits_current_task is False
    assert plan.slices[2].fits_current_task is False
    assert plan.initial_text == "第一段命运之轮转动。"
    assert plan.pending_text == "第二段利维坦苏醒。\n\n第三段世界线偏移。"


def test_plan_context_slices_splits_oversized_single_paragraph_into_safe_chunks():
    text = "命运之轮开始转动利维坦从深渊苏醒世界线发生偏移"
    budget = ContextBudget(max_context_tokens=12, reserved_output_tokens=2)

    plan = plan_context_slices(text, budget)

    assert plan.available_input_tokens == 10
    assert len(plan.slices) > 1
    assert all(item.estimated_tokens <= plan.available_input_tokens for item in plan.slices)
    assert plan.slices[0].fits_current_task is True
    assert any(not item.fits_current_task for item in plan.slices[1:])
    assert plan.initial_text
    assert plan.pending_text
