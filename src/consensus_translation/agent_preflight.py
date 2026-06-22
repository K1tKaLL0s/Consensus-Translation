from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from consensus_translation.agent_context import (
    ContextBudget,
    ContextSlice,
    estimate_context_tokens,
    plan_context_slices,
)
from consensus_translation.agent_contracts import AgentMode, policy_for_mode
from consensus_translation.agent_evaluators import TranslationEvaluator
from consensus_translation.agent_providers import ModelProvider


@dataclass(frozen=True)
class RemoteCallPreview:
    provider_id: str
    input_ref: str
    round_index: int
    text_preview: str
    estimated_input_tokens: int
    estimated_cost: float
    data_scopes: tuple[str, ...] = ("source",)


@dataclass(frozen=True)
class RemoteCallPreflight:
    confirmation_id: str
    requires_confirmation: bool
    estimated_input_tokens: int
    available_input_tokens: int
    total_estimated_cost: float
    budget_limit: float
    budget_exceeded: bool
    calls: list[RemoteCallPreview]
    warnings: list[str]


def _planned_tasks(text: str, budget: ContextBudget) -> list[tuple[str, str, int]]:
    plan = plan_context_slices(text, budget)
    initial_slices = [item for item in plan.slices if item.fits_current_task]
    continuation_slices = [item for item in plan.slices if not item.fits_current_task]
    tasks: list[tuple[str, str, int]] = []

    if initial_slices:
        initial_text = plan.initial_text
        tasks.append(
            (
                "context-initial",
                initial_text,
                sum(item.estimated_tokens for item in initial_slices),
            )
        )
    elif continuation_slices:
        first_slice = continuation_slices[0]
        tasks.append(
            (
                f"context-slice:{first_slice.index}",
                first_slice.text,
                first_slice.estimated_tokens,
            )
        )
        continuation_slices = continuation_slices[1:]
    elif text.strip():
        tasks.append(("context-initial", text.strip(), estimate_context_tokens(text)))

    for item in continuation_slices:
        tasks.append((f"context-slice:{item.index}", item.text, item.estimated_tokens))
    return tasks


def _confirmation_id(
    text: str,
    mode: AgentMode | str,
    providers: list[ModelProvider],
    context_budget: ContextBudget,
    api_enabled: bool,
    budget_limit: float,
    calls: list[RemoteCallPreview],
    training_text: str | None,
    validation_text: str | None,
    allow_training_upload: bool,
) -> str:
    payload = {
        "text": text,
        "mode": str(AgentMode(mode).value),
        "providers": [provider.provider_id for provider in providers],
        "max_context_tokens": context_budget.max_context_tokens,
        "reserved_output_tokens": context_budget.reserved_output_tokens,
        "api_enabled": api_enabled,
        "budget_limit": budget_limit,
        "allow_training_upload": allow_training_upload,
        "training_digest": hashlib.sha256(
            (training_text or "").encode("utf-8")
        ).hexdigest(),
        "validation_digest": hashlib.sha256(
            (validation_text or "").encode("utf-8")
        ).hexdigest(),
        "calls": [
            {
                "provider_id": call.provider_id,
                "input_ref": call.input_ref,
                "round_index": call.round_index,
                "estimated_input_tokens": call.estimated_input_tokens,
                "estimated_cost": call.estimated_cost,
                "data_scopes": list(call.data_scopes),
            }
            for call in calls
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return "preflight-" + hashlib.sha256(encoded).hexdigest()[:16]


def build_remote_call_preflight(
    text: str,
    mode: AgentMode | str,
    providers: list[ModelProvider],
    context_budget: ContextBudget,
    api_enabled: bool,
    budget_limit: float,
    evaluator: TranslationEvaluator | None = None,
    training_text: str | None = None,
    validation_text: str | None = None,
    allow_training_upload: bool = False,
) -> RemoteCallPreflight:
    remote_providers = [
        provider for provider in providers if provider.requires_api and api_enabled
    ]
    tasks = _planned_tasks(text, context_budget)
    policy = policy_for_mode(mode, api_enabled=api_enabled, budget_limit=budget_limit)
    remote_evaluator = (
        evaluator
        if (
            evaluator is not None
            and evaluator.requires_api
            and api_enabled
            and policy.validation_required
        )
        else None
    )

    calls: list[RemoteCallPreview] = []
    training_tokens = estimate_context_tokens(training_text or "")
    validation_tokens = estimate_context_tokens(validation_text or "")
    for input_ref, task_text, token_count in tasks:
        for round_index in range(1, policy.max_rounds + 1):
            for provider in remote_providers:
                provider_scopes = ("source",)
                provider_tokens = token_count
                if training_text and allow_training_upload:
                    provider_scopes = ("source", "training")
                    provider_tokens += training_tokens
                calls.append(
                    RemoteCallPreview(
                        provider_id=provider.provider_id,
                        input_ref=input_ref,
                        round_index=round_index,
                        text_preview=task_text[:120],
                        estimated_input_tokens=provider_tokens,
                        estimated_cost=provider.estimated_cost,
                        data_scopes=provider_scopes,
                    )
                )
            if remote_evaluator is not None:
                evaluator_scopes = ("source", "candidate")
                if validation_text:
                    evaluator_scopes += ("validation",)
                calls.append(
                    RemoteCallPreview(
                        provider_id=f"evaluator:{remote_evaluator.evaluator_id}",
                        input_ref=input_ref,
                        round_index=round_index,
                        text_preview=task_text[:120],
                        estimated_input_tokens=(
                            token_count * 2 + validation_tokens
                        ),
                        estimated_cost=remote_evaluator.estimated_cost,
                        data_scopes=evaluator_scopes,
                    )
                )

    total_estimated_cost = round(
        sum(call.estimated_cost for call in calls),
        8,
    )
    warnings = []
    if remote_providers and training_text and not allow_training_upload:
        warnings.append("training_upload_disabled")
    if policy.validation_required and not validation_text:
        warnings.append("validation_data_missing")
    if total_estimated_cost > budget_limit:
        warnings.append("budget_exceeded:estimated_remote_cost")
    confirmation_id = _confirmation_id(
        text=text,
        mode=mode,
        providers=providers,
        context_budget=context_budget,
        api_enabled=api_enabled,
        budget_limit=budget_limit,
        calls=calls,
        training_text=training_text,
        validation_text=validation_text,
        allow_training_upload=allow_training_upload,
    )
    return RemoteCallPreflight(
        confirmation_id=confirmation_id,
        requires_confirmation=bool(calls),
        estimated_input_tokens=estimate_context_tokens(text),
        available_input_tokens=context_budget.available_input_tokens,
        total_estimated_cost=total_estimated_cost,
        budget_limit=budget_limit,
        budget_exceeded=total_estimated_cost > budget_limit,
        calls=calls,
        warnings=warnings,
    )
