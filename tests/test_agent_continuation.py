from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_context import ContextBudget
from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_continuation import run_context_managed_translation
from consensus_translation.agent_contracts import TranslationCandidate
from consensus_translation.agent_evaluators import EvaluationResult
from consensus_translation.agent_providers import EchoModelProvider


class CapturingBriefProvider:
    provider_id = "capture-brief"
    requires_api = False
    estimated_cost = 0.0

    def __init__(self):
        self.requests = []

    def translate(self, request):
        self.requests.append(request)
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=f"ZH:{request.text}",
            confidence=0.9,
        )


class PassingEvaluator:
    evaluator_id = "passing"
    requires_api = False
    estimated_cost = 0.0

    def __init__(self):
        self.requests = []

    def evaluate(self, request):
        self.requests.append(request)
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=0.9,
            metrics={"score": 0.9},
        )


def test_context_managed_translation_processes_all_initial_fit_slices_before_continuing():
    text = "alpha beta\n\ngamma delta\n\nomega zeta"

    result = run_context_managed_translation(
        text=text,
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[EchoModelProvider("echo-local", prefix="ZH:")],
        context_budget=ContextBudget(max_context_tokens=7, reserved_output_tokens=2),
        api_enabled=False,
        budget_limit=0.0,
        allow_mock_providers=True,
    )

    assert result.context_plan.initial_text == "alpha beta\n\ngamma delta"
    assert result.context_plan.pending_text == "omega zeta"
    assert result.initial_task.source_text == "alpha beta\n\ngamma delta"
    assert [task.source_text for task in result.continuation_tasks] == ["omega zeta"]
    assert result.final_text == "ZH:alpha beta\n\ngamma delta\n\nZH:omega zeta"


def test_context_managed_translation_creates_initial_continuation_and_stitch_tasks():
    text = "第一段命运之轮转动。\n\n第二段利维坦苏醒。\n\n第三段世界线偏移。"

    result = run_context_managed_translation(
        text=text,
        source_lang="zh",
        target_lang="ja",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[EchoModelProvider("echo-local", prefix="JP:")],
        context_budget=ContextBudget(max_context_tokens=18, reserved_output_tokens=5),
        api_enabled=False,
        budget_limit=0.0,
        allow_mock_providers=True,
    )

    assert result.context_plan.initial_text == "第一段命运之轮转动。"
    assert result.context_plan.pending_text == "第二段利维坦苏醒。\n\n第三段世界线偏移。"
    assert result.initial_task.task_type == "initial_translation"
    assert result.initial_task.task_id.startswith("task-")
    assert [task.task_type for task in result.continuation_tasks] == [
        "continuation_translation",
        "continuation_translation",
    ]
    assert all(task.task_id.startswith("task-") for task in result.continuation_tasks)
    assert all(
        task.inherited_brief == result.translation_brief
        for task in result.continuation_tasks
    )
    assert result.stitch_task.task_type == "stitch_and_verify"
    assert result.stitch_task.task_id.startswith("task-")
    assert result.stitch_task.source_task_ids == [
        result.initial_task.run.contract.run_id,
        *[task.run.contract.run_id for task in result.continuation_tasks],
    ]
    assert result.final_text == (
        "JP:第一段命运之轮转动。\n\n"
        "JP:第二段利维坦苏醒。\n\n"
        "JP:第三段世界线偏移。"
    )
    assert result.verification["segment_count"] == 3
    assert result.verification["empty_segment_count"] == 0
    assert result.verification["order_preserved"] is True
    assert result.verification["status"] == "passed"
    assert result.stitch_task.verification == result.verification
    assert result.stitch_task.verification["source_task_ids"] == result.stitch_task.source_task_ids
    assert "写作结构" in result.translation_brief
    assert "翻译要点" in result.translation_brief
    assert "待续策略" in result.translation_brief
    assert "前序摘要" in result.translation_brief


def test_context_managed_translation_records_runtime_context_checks():
    text = "命运之轮开始转动利维坦从深渊苏醒世界线发生偏移"

    result = run_context_managed_translation(
        text=text,
        source_lang="zh",
        target_lang="ja",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[EchoModelProvider("echo-local", prefix="JP:")],
        context_budget=ContextBudget(max_context_tokens=12, reserved_output_tokens=2),
        api_enabled=False,
        budget_limit=0.0,
        allow_mock_providers=True,
    )

    all_tasks = [result.initial_task, *result.continuation_tasks]
    assert len(all_tasks) > 1
    for task in all_tasks:
        assert task.run is not None
        assert any(
            item.startswith("context_check:within_limit")
            for item in task.run.contract.trace
        )
    assert result.verification["context_limit_respected"] is True


def test_continuation_provider_requests_receive_inherited_translation_brief():
    provider = CapturingBriefProvider()

    result = run_context_managed_translation(
        text="alpha beta\n\ngamma delta\n\nomega zeta",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[provider],
        context_budget=ContextBudget(max_context_tokens=7, reserved_output_tokens=2),
        api_enabled=False,
        budget_limit=0.0,
    )

    assert provider.requests[0].continuation_brief is None
    assert [request.continuation_brief for request in provider.requests[1:]] == [
        result.translation_brief
    ]
    assert "写作结构" in provider.requests[1].continuation_brief
    assert "翻译要点" in provider.requests[1].continuation_brief


def test_context_managed_translation_passes_training_and_validation_to_workflow():
    provider = CapturingBriefProvider()
    evaluator = PassingEvaluator()

    result = run_context_managed_translation(
        text="source paragraph",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.SELF_ITERATIVE,
        providers=[provider],
        context_budget=ContextBudget(max_context_tokens=64, reserved_output_tokens=8),
        api_enabled=False,
        budget_limit=0.0,
        training_text="training example",
        validation_text="reference translation",
        evaluator=evaluator,
    )

    assert result.final_text == "ZH:source paragraph"
    assert provider.requests[0].training_text == "training example"
    assert evaluator.requests[0].reference_text == "reference translation"
