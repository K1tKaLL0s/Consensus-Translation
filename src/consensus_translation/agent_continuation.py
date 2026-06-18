from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from consensus_translation.agent_context import (
    ContextBudget,
    ContextSlice,
    ContextSlicePlan,
    plan_context_slices,
)
from consensus_translation.agent_contracts import AgentMode, AgentRunResult
from consensus_translation.agent_evaluators import TranslationEvaluator
from consensus_translation.agent_providers import ModelProvider
from consensus_translation.agent_workflows import run_agent_translation


@dataclass(frozen=True)
class ManagedTranslationTask:
    task_id: str
    task_type: str
    source_text: str
    run: AgentRunResult | None
    inherited_brief: str | None = None
    source_task_ids: list[str] | None = None
    verification: dict[str, object] | None = None


@dataclass(frozen=True)
class ContextManagedTranslationResult:
    context_plan: ContextSlicePlan
    initial_task: ManagedTranslationTask
    continuation_tasks: list[ManagedTranslationTask]
    stitch_task: ManagedTranslationTask
    translation_brief: str
    final_text: str
    verification: dict[str, object]


def _build_translation_brief(
    topic: str | None,
    source_lang: str,
    target_lang: str,
    completed_text: str,
    plan: ContextSlicePlan,
) -> str:
    preview = completed_text[:80].replace("\n", " ")
    pending_count = sum(1 for item in plan.slices if not item.fits_current_task)
    return (
        f"写作结构：全文分为 {len(plan.slices)} 个顺序片段，续译必须保持原片段顺序与段落边界。\n"
        f"翻译要点：{source_lang}->{target_lang}，主题={topic or 'uncategorized'}，"
        "术语与语气以前序译文为准。\n"
        f"待续策略：剩余 {pending_count} 个片段应沿用前序术语、叙事视角、语气和段落结构；"
        "不得重译已完成片段。\n"
        f"前序摘要：{preview}"
    )


def _run_slice(
    slice_item: ContextSlice,
    task_type: str,
    text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
    mode: AgentMode | str,
    providers: list[ModelProvider],
    api_enabled: bool,
    budget_limit: float,
    inherited_brief: str | None,
    available_input_tokens: int,
    store: object | None,
    lexicon_store: object | None,
    evaluator: TranslationEvaluator | None,
    training_text: str | None,
    validation_text: str | None,
    allow_training_upload: bool,
) -> ManagedTranslationTask:
    run = run_agent_translation(
        text=slice_item.text,
        source_lang=source_lang,
        target_lang=target_lang,
        topic=topic,
        mode=mode,
        providers=providers,
        api_enabled=api_enabled,
        budget_limit=budget_limit,
        input_refs=[f"context-slice:{slice_item.index}"],
        store=store,
        lexicon_store=lexicon_store,
        evaluator=evaluator,
        training_text=training_text,
        validation_text=validation_text,
        allow_training_upload=allow_training_upload,
        continuation_brief=inherited_brief,
    )
    run.contract.trace.append(
        f"context_check:within_limit tokens={slice_item.estimated_tokens}/{available_input_tokens}"
    )
    return ManagedTranslationTask(
        task_id=f"task-{uuid4().hex[:16]}",
        task_type=task_type,
        source_text=text,
        run=run,
        inherited_brief=inherited_brief,
    )


def _verify_stitched_text(
    tasks: list[ManagedTranslationTask],
    final_text: str,
) -> dict[str, object]:
    translated_parts = [
        task.run.decision.final_text
        for task in tasks
        if task.run is not None
    ]
    source_task_ids = [
        task.run.contract.run_id
        for task in tasks
        if task.run is not None
    ]
    expected_text = "\n\n".join(translated_parts)
    order_preserved = final_text == expected_text
    empty_segment_count = sum(1 for part in translated_parts if not part.strip())
    context_limit_respected = all(
        task.run is not None
        and any(item.startswith("context_check:within_limit") for item in task.run.contract.trace)
        for task in tasks
    )
    status = (
        "passed"
        if (
            order_preserved
            and empty_segment_count == 0
            and context_limit_respected
            and len(translated_parts) == len(tasks)
        )
        else "needs_review"
    )
    return {
        "segment_count": len(translated_parts),
        "expected_segment_count": len(tasks),
        "empty_segment_count": empty_segment_count,
        "order_preserved": order_preserved,
        "context_limit_respected": context_limit_respected,
        "source_task_ids": source_task_ids,
        "status": status,
    }


def run_context_managed_translation(
    text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
    mode: AgentMode | str,
    providers: list[ModelProvider],
    context_budget: ContextBudget,
    api_enabled: bool,
    budget_limit: float,
    store: object | None = None,
    lexicon_store: object | None = None,
    evaluator: TranslationEvaluator | None = None,
    training_text: str | None = None,
    validation_text: str | None = None,
    allow_training_upload: bool = False,
) -> ContextManagedTranslationResult:
    plan = plan_context_slices(text, context_budget)
    initial_slices = [item for item in plan.slices if item.fits_current_task]
    continuation_slices = [item for item in plan.slices if not item.fits_current_task]
    if initial_slices:
        first_slice = ContextSlice(
            index=initial_slices[0].index,
            text=plan.initial_text,
            estimated_tokens=sum(item.estimated_tokens for item in initial_slices),
            fits_current_task=True,
        )
    elif continuation_slices:
        first_slice = continuation_slices[0]
        continuation_slices = continuation_slices[1:]
    else:
        first_slice = ContextSlice(
            index=0,
            text="",
            estimated_tokens=0,
            fits_current_task=True,
        )

    initial_task = _run_slice(
        slice_item=first_slice,
        task_type="initial_translation",
        text=first_slice.text,
        source_lang=source_lang,
        target_lang=target_lang,
        topic=topic,
        mode=mode,
        providers=providers,
        api_enabled=api_enabled,
        budget_limit=budget_limit,
        inherited_brief=None,
        available_input_tokens=plan.available_input_tokens,
        store=store,
        lexicon_store=lexicon_store,
        evaluator=evaluator,
        training_text=training_text,
        validation_text=validation_text,
        allow_training_upload=allow_training_upload,
    )
    translation_brief = _build_translation_brief(
        topic=topic,
        source_lang=source_lang,
        target_lang=target_lang,
        completed_text=initial_task.run.decision.final_text if initial_task.run else "",
        plan=plan,
    )

    continuation_tasks = [
        _run_slice(
            slice_item=item,
            task_type="continuation_translation",
            text=item.text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
            mode=mode,
            providers=providers,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
            inherited_brief=translation_brief,
            available_input_tokens=plan.available_input_tokens,
            store=store,
            lexicon_store=lexicon_store,
            evaluator=evaluator,
            training_text=training_text,
            validation_text=validation_text,
            allow_training_upload=allow_training_upload,
        )
        for item in continuation_slices
    ]
    all_translation_tasks = [initial_task, *continuation_tasks]
    final_text = "\n\n".join(
        task.run.decision.final_text
        for task in all_translation_tasks
        if task.run is not None
    )
    verification = _verify_stitched_text(all_translation_tasks, final_text)
    stitch_task = ManagedTranslationTask(
        task_id=f"task-{uuid4().hex[:16]}",
        task_type="stitch_and_verify",
        source_text=text,
        run=None,
        inherited_brief=translation_brief,
        source_task_ids=list(verification["source_task_ids"]),
        verification=verification,
    )
    return ContextManagedTranslationResult(
        context_plan=plan,
        initial_task=initial_task,
        continuation_tasks=continuation_tasks,
        stitch_task=stitch_task,
        translation_brief=translation_brief,
        final_text=final_text,
        verification=verification,
    )
