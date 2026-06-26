from __future__ import annotations

from dataclasses import replace

from consensus_translation.agent_consensus import (
    align_translation_candidates,
    arbitrate_consensus_result,
    collect_consensus_candidates,
    normalize_translation_candidate,
)
from consensus_translation.agent_contracts import (
    AgentMode,
    AgentRunContract,
    AgentRunResult,
    AgentRunStatus,
    ConsensusDecision,
    LexiconUpdateProposal,
    ModePolicy,
    TranslationCandidate,
    policy_for_mode,
)
from consensus_translation.agent_feedback import RatingSignalSummary
from consensus_translation.agent_finalize import finalize_agent_contract
from consensus_translation.agent_evaluators import (
    DeterministicTranslationEvaluator,
    EvaluationRequest,
    TranslationEvaluator,
)
from consensus_translation.agent_inputs import AgentInputDocument
from consensus_translation.agent_meta_policy import MetaPolicyAgent, MetaPolicyContext
from consensus_translation.agent_providers import ModelProvider, ProviderRequest
from consensus_translation.agent_workflow_state import (
    WorkflowEvent,
    WorkflowState,
    WorkflowStateMachine,
    workflow_trace_label,
)
from consensus_translation.domain_signals import extract_domain_signals
from consensus_translation.mdwc import MDWCContext


VALIDATION_PASS_THRESHOLD = 0.75
MAX_CLOUD_PROVIDERS = 3

def _string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item) for item in value)
    return ()


def _record_workflow_event(
    contract: AgentRunContract,
    workflow: WorkflowStateMachine,
    event: WorkflowEvent,
) -> None:
    state = workflow.apply(event)
    label = workflow_trace_label(state)
    if not contract.trace or contract.trace[-1] != label:
        contract.trace.append(label)


def _provider_is_cloud(provider: ModelProvider) -> bool:
    return (
        getattr(provider, "requires_api", False)
        or getattr(provider, "provider_kind", "") == "cloud"
    )


def _provider_is_mock(provider: ModelProvider) -> bool:
    return bool(getattr(provider, "is_mock", False)) or str(
        getattr(provider, "provider_kind", "")
    ).lower() == "mock"


def _mock_provider_ids(providers: list[ModelProvider]) -> list[str]:
    return [
        str(getattr(provider, "provider_id", "<unknown>"))
        for provider in providers
        if _provider_is_mock(provider)
    ]


def _limited_cloud_provider_set(
    providers: list[ModelProvider],
) -> tuple[list[ModelProvider], list[ModelProvider]]:
    active_providers: list[ModelProvider] = []
    skipped_providers: list[ModelProvider] = []
    cloud_count = 0
    for provider in providers:
        if _provider_is_cloud(provider):
            cloud_count += 1
            if cloud_count > MAX_CLOUD_PROVIDERS:
                skipped_providers.append(provider)
                continue
        active_providers.append(provider)
    return active_providers, skipped_providers

def _empty_decision(reason: str) -> ConsensusDecision:
    return ConsensusDecision(
        final_text="",
        final_score=0.0,
        vote_map={},
        mdwc_scores={},
        conflict_points=[],
        decision_reason=reason,
    )


def _normalized_rating(value: float) -> float:
    return min(max(value / 5.0, 0.0), 1.0) if value > 0 else 0.0


def _rating_summary_from_store(
    store: object | None,
    *,
    topic: str | None,
    source_lang: str,
    target_lang: str,
    mode: AgentMode,
    provider_ids: tuple[str, ...],
) -> RatingSignalSummary:
    if store is None:
        return RatingSignalSummary()
    summarizer = getattr(store, "rating_signal_summary", None)
    if not callable(summarizer):
        return RatingSignalSummary()
    return summarizer(
        topic=topic or "uncategorized",
        source_language=source_lang,
        target_language=target_lang,
        mode=mode.value,
        provider_ids=provider_ids,
    )


def _trace_rating_summary(trace: list[str], summary: RatingSignalSummary) -> None:
    if summary.sample_count <= 0:
        return
    trace.append(f"rating_signal:sample_count={summary.sample_count}")
    trace.append(f"rating_signal:topic_average={summary.topic_average_rating:.6f}")
    trace.append(f"rating_signal:provider_average={summary.provider_average_rating:.6f}")
    trace.append(f"rating_signal:recent_low={summary.recent_low_rating_count}")
    trace.append(f"rating_signal:mdwc_user_mismatch={summary.mdwc_user_mismatch_rate:.6f}")


def _decide(
    candidates: list[TranslationCandidate],
    *,
    source_text: str = "",
    glossary_matches: dict[str, str] | None = None,
    translation_memory_matches: dict[str, str] | None = None,
    rating_summary: RatingSignalSummary | None = None,
    topic_match_score: float = 0.0,
    validation_coverage: float = 0.0,
    budget_spent: float = 0.0,
    budget_limit: float = 0.0,
    iteration_count: int = 1,
    special_marker_count: int = 0,
) -> ConsensusDecision:
    summary = rating_summary or RatingSignalSummary()
    collected = collect_consensus_candidates(
        source_text=source_text,
        provider_candidates=candidates,
        glossary_matches=glossary_matches or {},
        translation_memory_matches=translation_memory_matches or {},
    )
    if not collected.candidates:
        return _empty_decision("no-candidates")

    alignment = align_translation_candidates(
        source_text=source_text,
        candidates=collected.candidates,
        glossary_matches=glossary_matches or {},
    )
    decision = arbitrate_consensus_result(
        candidates=collected.candidates,
        alignment=alignment,
        mdwc_context=MDWCContext(
            topic_match_score=topic_match_score,
            validation_coverage=validation_coverage,
            budget_spent=budget_spent,
            budget_limit=budget_limit,
            iteration_count=iteration_count,
            special_marker_count=special_marker_count,
            user_rating_signal=summary.user_rating_signal,
            provider_historical_rating=_normalized_rating(summary.provider_average_rating),
            topic_historical_rating=_normalized_rating(summary.topic_average_rating),
            mode_historical_rating=_normalized_rating(summary.mode_average_rating),
            low_rating_penalty=summary.low_rating_penalty,
            high_rating_boost=summary.high_rating_boost,
            mdwc_user_mismatch_rate=summary.mdwc_user_mismatch_rate,
        ),
    )
    return ConsensusDecision(
        final_text=decision.final_text,
        final_score=decision.final_score,
        vote_map={candidate.provider_id: 1 for candidate in candidates},
        mdwc_scores=decision.mdwc_scores,
        conflict_points=decision.conflict_points,
        decision_reason=decision.decision_reason,
        confidence_level=decision.confidence_level,
        accepted_segments=decision.accepted_segments,
        rejected_segments=decision.rejected_segments,
        arbitration_reason=decision.arbitration_reason,
        requires_human_review=decision.requires_human_review,
        aligned_segments=decision.aligned_segments,
        scoring_dimensions=decision.scoring_dimensions,
    )

def _build_memory_proposals(
    text: str,
    topic: str | None,
    decision: ConsensusDecision,
    policy: ModePolicy,
    mode: AgentMode,
) -> list[LexiconUpdateProposal]:
    if not decision.final_text:
        return []
    update_source = (
        "pretraining_draft"
        if mode == AgentMode.PRETRAINING
        else "agent_proposal"
    )
    rationale = (
        "pretraining-draft-candidate"
        if mode == AgentMode.PRETRAINING
        else "agent-final-candidate"
    )
    return [
        LexiconUpdateProposal(
            topic=topic or "uncategorized",
            layer="terms",
            source=text,
            target=decision.final_text,
            rationale=rationale,
            confidence=decision.final_score,
            requires_user_confirm=policy.human_gate_required,
            update_source=update_source,
        )
    ]


def _empty_lexicon_matches() -> dict[str, dict[str, str]]:
    return {"terms": {}, "phrases": {}, "style_rules": {}}


def _count_special_markers(
    lexicon_store: object | None,
    topic: str | None,
    text: str,
) -> int:
    if lexicon_store is None:
        return 0
    counter = getattr(lexicon_store, "count_special_entries", None)
    if counter is None:
        return 0
    return int(counter(topic, text))
def _count_user_corrections(
    lexicon_store: object | None,
    topic: str | None,
    text: str,
) -> int:
    if lexicon_store is None:
        return 0
    counter = getattr(lexicon_store, "count_user_corrections", None)
    if counter is None:
        return 0
    return int(counter(topic, text))
def _collect_lexicon_matches(
    lexicon_store: object | None,
    topic: str | None,
    text: str,
) -> dict[str, dict[str, str]]:
    if lexicon_store is None:
        return _empty_lexicon_matches()

    finder = getattr(lexicon_store, "find_matching_lexicon_entries", None)
    if finder is not None:
        matches = finder(topic, text)
        return {
            "terms": dict(matches.get("terms", {})),
            "phrases": dict(matches.get("phrases", {})),
            "style_rules": dict(matches.get("style_rules", {})),
        }

    exporter = getattr(lexicon_store, "export_topic", None)
    if exporter is None:
        return _empty_lexicon_matches()

    exported = exporter(topic)
    if not isinstance(exported, dict):
        return _empty_lexicon_matches()
    return {
        layer: {
            source: target
            for source, target in dict(exported.get(layer, {})).items()
            if source and source in text
        }
        for layer in ("terms", "phrases", "style_rules")
    }


def run_agent_translation(
    text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
    mode: AgentMode | str,
    providers: list[ModelProvider],
    api_enabled: bool,
    budget_limit: float,
    training_text: str | None = None,
    validation_text: str | None = None,
    input_refs: list[str] | None = None,
    store: object | None = None,
    lexicon_store: object | None = None,
    evaluator: TranslationEvaluator | None = None,
    continuation_brief: str | None = None,
    allow_training_upload: bool = False,
    allow_mock_providers: bool = False,
) -> AgentRunResult:
    requested_mode = AgentMode(mode)
    effective_mode = requested_mode
    trace: list[str] = []
    meta_decision = None
    active_lexicon_store = lexicon_store or store
    mock_provider_ids = _mock_provider_ids(providers)
    if mock_provider_ids and not allow_mock_providers:
        raise PermissionError(
            "mock providers are disabled for production workflow runs: "
            + ", ".join(mock_provider_ids)
        )
    domain_signals = extract_domain_signals(text)
    domain_tags = _string_tuple(domain_signals["domain_tags"])
    domain_tag_count = len(domain_tags)
    topic_match_score = min(domain_tag_count / 3.0, 1.0)
    special_marker_count = _count_special_markers(active_lexicon_store, topic, text)
    user_correction_count = _count_user_corrections(active_lexicon_store, topic, text)

    provider_ids = tuple(
        str(getattr(provider, "provider_id", ""))
        for provider in providers
        if str(getattr(provider, "provider_id", "")).strip()
    )
    rating_summary = _rating_summary_from_store(
        active_lexicon_store,
        topic=topic,
        source_lang=source_lang,
        target_lang=target_lang,
        mode=requested_mode,
        provider_ids=provider_ids,
    )

    if requested_mode == AgentMode.SELF_DECISION:
        trace.append("workflow:metaPolicyDeciding")
        meta_context = MetaPolicyContext(
            task_text=text,
            topic_match_score=topic_match_score,
            domain_tag_count=domain_tag_count,
            special_marker_count=special_marker_count,
            user_correction_count=user_correction_count,
            high_risk_term_count=special_marker_count,
            local_provider_count=sum(1 for provider in providers if not _provider_is_cloud(provider)),
            cloud_provider_count=sum(1 for provider in providers if _provider_is_cloud(provider)),
            topic_average_rating=rating_summary.topic_average_rating,
            language_pair_average_rating=rating_summary.language_pair_average_rating,
            provider_average_rating=rating_summary.provider_average_rating,
            recent_low_rating_count=rating_summary.recent_low_rating_count,
            mdwc_user_mismatch_rate=rating_summary.mdwc_user_mismatch_rate,
            terminology_issue_ratio=rating_summary.terminology_issue_ratio,
            style_issue_ratio=rating_summary.style_issue_ratio,
            lore_issue_ratio=rating_summary.lore_issue_ratio,
            rating_sample_count=rating_summary.sample_count,
        )
        meta_decision = MetaPolicyAgent().select_mode(
            training_text=training_text,
            validation_text=validation_text,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
            context=meta_context,
        )
        effective_mode = meta_decision.selected_mode
        trace.append(f"meta_policy:selected_mode={effective_mode.value}")
        trace.append(f"meta_policy:reason={meta_decision.reason}")
        trace.append(
            f"meta_policy:validation_coverage={meta_decision.validation_coverage:.6f}"
        )
        trace.append(f"meta_policy:risk_level={meta_decision.risk_level}")
        trace.append(
            "meta_policy:requires_human_confirmation="
            f"{str(meta_decision.requires_human_confirmation).lower()}"
        )
        trace.append(f"meta_policy:max_iterations={meta_decision.max_iterations}")
        trace.append(f"meta_policy:budget_limit={meta_decision.budget_limit:.6f}")
        trace.append(f"meta_policy:fallback_plan={meta_decision.fallback_plan}")
        trace.append(f"meta_policy:domain_tag_count={meta_context.domain_tag_count}")
        trace.append(f"meta_policy:special_marker_count={meta_context.special_marker_count}")
        trace.append(f"meta_policy:user_correction_count={meta_context.user_correction_count}")
        trace.append(f"meta_policy:rating_sample_count={meta_context.rating_sample_count}")
        trace.append(f"meta_policy:recent_low_rating_count={meta_context.recent_low_rating_count}")
        trace.append(f"meta_policy:mdwc_user_mismatch_rate={meta_context.mdwc_user_mismatch_rate:.6f}")

    policy = policy_for_mode(effective_mode, api_enabled, budget_limit)
    if meta_decision is not None:
        policy = replace(
            policy,
            max_rounds=meta_decision.max_iterations,
            human_gate_required=meta_decision.requires_human_confirmation,
            budget_limit=meta_decision.budget_limit,
        )
    if policy.validation_required and (not training_text or not validation_text):
        raise ValueError(
            f"{effective_mode.value} mode requires training_text and validation_text"
        )

    if effective_mode == AgentMode.PRETRAINING:
        trace.append("workflow:pretrainingPreparing")
        trace.append("pretraining:training_loaded")
        trace.append("pretraining:validation_loaded")

    active_providers, skipped_cloud_providers = (
        _limited_cloud_provider_set(providers)
        if policy.api_enabled
        else (providers, [])
    )
    contract = AgentRunContract.new_run(
        mode=requested_mode,
        input_refs=input_refs or ["inline:text"],
        provider_ids=[provider.provider_id for provider in active_providers],
        policy=policy,
    )
    contract.trace.extend(trace)
    for provider in skipped_cloud_providers:
        contract.trace.append(
            f"provider_skipped:{provider.provider_id}:cloud_provider_limit"
        )
    for provider_id in mock_provider_ids:
        contract.trace.append(f"mock_provider_allowed:{provider_id}")
    workflow = WorkflowStateMachine()
    _record_workflow_event(contract, workflow, WorkflowEvent.START_TRANSLATION)
    if domain_tags:
        contract.trace.append("domain_tags:" + ",".join(domain_tags))
    lexicon_matches = _collect_lexicon_matches(active_lexicon_store, topic, text)
    if any(lexicon_matches[layer] for layer in lexicon_matches):
        contract.trace.append(
            "lexicon_hits:"
            + ",".join(
                f"{layer}={len(lexicon_matches[layer])}"
                for layer in ("terms", "phrases", "style_rules")
            )
        )
    if special_marker_count > 0:
        contract.trace.append(f"special_markers:{special_marker_count}")
    _trace_rating_summary(contract.trace, rating_summary)

    candidates: list[TranslationCandidate] = []
    decision = _empty_decision("not-run")
    stop_for_budget = False
    validation_passed = not policy.validation_required
    active_evaluator: TranslationEvaluator = evaluator or DeterministicTranslationEvaluator()

    for round_index in range(1, policy.max_rounds + 1):
        contract.trace.append(f"round:{round_index}")
        local_translation_started = any(not _provider_is_cloud(provider) for provider in active_providers)
        cloud_translation_started = any(
            _provider_is_cloud(provider)
            and (policy.api_enabled or not getattr(provider, "requires_api", False))
            for provider in active_providers
        )
        if local_translation_started:
            _record_workflow_event(
                contract,
                workflow,
                WorkflowEvent.LOCAL_TRANSLATION_DONE,
            )
        if cloud_translation_started and not local_translation_started:
            _record_workflow_event(
                contract,
                workflow,
                WorkflowEvent.CLOUD_TRANSLATION_DONE,
            )
        for provider in active_providers:
            if provider.requires_api and not policy.api_enabled:
                contract.trace.append(f"provider_skipped:{provider.provider_id}:api_disabled")
                continue

            next_cost = contract.budget["spent"] + provider.estimated_cost
            if next_cost > policy.budget_limit:
                contract.trace.append(f"budget_exceeded:{provider.provider_id}")
                contract.trace.append("workflow:budgetExceeded")
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.ERROR_OCCURRED,
                )
                contract.status = AgentRunStatus.BUDGET_EXCEEDED
                stop_for_budget = True
                break

            candidate = normalize_translation_candidate(provider.translate(
                ProviderRequest(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    topic=topic,
                    round_index=round_index,
                    training_text=(
                        training_text
                        if (not provider.requires_api or allow_training_upload)
                        else None
                    ),
                    continuation_brief=continuation_brief,
                    conflict_points=decision.conflict_points,
                    lexicon_terms=lexicon_matches["terms"],
                    lexicon_phrases=lexicon_matches["phrases"],
                    style_rules=lexicon_matches["style_rules"],
                )
            ))
            contract.budget["spent"] += candidate.cost
            candidates.append(candidate)

        if stop_for_budget:
            break

        if candidates and workflow.state == WorkflowState.LOCAL_TRANSLATING:
            _record_workflow_event(
                contract,
                workflow,
                WorkflowEvent.LOCAL_TRANSLATION_DONE,
            )
        if cloud_translation_started and workflow.state in {
            WorkflowState.LOCAL_TRANSLATING,
            WorkflowState.LOCAL_REVIEWING,
        }:
            _record_workflow_event(
                contract,
                workflow,
                WorkflowEvent.CLOUD_TRANSLATION_DONE,
            )
        if cloud_translation_started and workflow.state == WorkflowState.CLOUD_TRANSLATING:
            _record_workflow_event(
                contract,
                workflow,
                WorkflowEvent.CROSSFIRE_DONE,
            )
        _record_workflow_event(contract, workflow, WorkflowEvent.CONSENSUS_DONE)
        decision = _decide(
            candidates,
            source_text=text,
            glossary_matches={
                **lexicon_matches["terms"],
                **lexicon_matches["phrases"],
            },
            translation_memory_matches={},
            rating_summary=rating_summary,
            topic_match_score=topic_match_score,
            validation_coverage=1.0 if validation_passed else 0.0,
            budget_spent=contract.budget["spent"],
            budget_limit=policy.budget_limit,
            iteration_count=round_index,
            special_marker_count=special_marker_count,
        )
        if policy.validation_required:
            contract.trace.append("workflow:validationChecking")
            if active_evaluator.requires_api and not policy.api_enabled:
                contract.trace.append(
                    f"validation_evaluator_skipped:{active_evaluator.evaluator_id}:api_disabled"
                )
                active_evaluator = DeterministicTranslationEvaluator()

            next_cost = contract.budget["spent"] + active_evaluator.estimated_cost
            if next_cost > policy.budget_limit:
                contract.trace.append(
                    f"budget_exceeded:{active_evaluator.evaluator_id}"
                )
                contract.trace.append("workflow:budgetExceeded")
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.ERROR_OCCURRED,
                )
                contract.status = AgentRunStatus.BUDGET_EXCEEDED
                stop_for_budget = True
                break

            evaluation = active_evaluator.evaluate(
                EvaluationRequest(
                    source_text=text,
                    candidate_text=decision.final_text,
                    reference_text=validation_text or "",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    topic=topic,
                    round_index=round_index,
                )
            )
            contract.budget["spent"] += evaluation.cost
            validation_score = evaluation.score
            contract.trace.append(f"validation_evaluator:{evaluation.evaluator_id}")
            contract.trace.append(
                f"validation_score:round={round_index}:overall={validation_score:.6f}"
            )
            if evaluation.requires_human_review:
                contract.trace.append(
                    f"validation_review_required:{evaluation.evaluator_id}"
                )
            if validation_score >= VALIDATION_PASS_THRESHOLD:
                validation_passed = True
                contract.trace.append(f"validation_passed:round={round_index}")
                break
        elif decision.final_score >= 0.75:
            break
        if stop_for_budget:
            break

    proposals = _build_memory_proposals(text, topic, decision, policy, effective_mode)
    if effective_mode == AgentMode.PRETRAINING and proposals:
        contract.trace.append("workflow:glossarySuggestion")

    if contract.status != AgentRunStatus.BUDGET_EXCEEDED:
        if not candidates:
            contract.status = AgentRunStatus.NEEDS_REVIEW
            if workflow.state != WorkflowState.FAILED:
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.ERROR_OCCURRED,
                )
            contract.trace.append("workflow:needsReview")
        elif policy.validation_required and not validation_passed:
            contract.status = AgentRunStatus.NEEDS_REVIEW
            contract.trace.append("validation_failed:max_rounds")
            if workflow.state == WorkflowState.CONSENSUS_SCORING:
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.ARBITRATION_DONE,
                )
            contract.trace.append("workflow:needsReview")
        elif policy.human_gate_required:
            contract.status = AgentRunStatus.AWAITING_HUMAN_CONFIRMATION
            contract.trace.append("human_gate:required")
            if workflow.state == WorkflowState.CONSENSUS_SCORING:
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.ARBITRATION_DONE,
                )
        elif decision.requires_human_review and not (
            policy.validation_required and validation_passed
        ):
            contract.status = AgentRunStatus.NEEDS_REVIEW
            contract.trace.append("finalize_guard:decision_requires_human_review")
            if workflow.state == WorkflowState.CONSENSUS_SCORING:
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.ARBITRATION_DONE,
                )
        else:
            if workflow.state == WorkflowState.CONSENSUS_SCORING:
                _record_workflow_event(
                    contract,
                    workflow,
                    WorkflowEvent.USER_CONFIRMED,
                )
            finalize_agent_contract(contract)

    result = AgentRunResult(
        contract=contract,
        candidates=candidates,
        decision=decision,
        lexicon_proposals=proposals,
    )
    if store is not None:
        record_result = getattr(store, "record_result", None)
        if callable(record_result):
            record_result(result)
    return result


def run_agent_batch_translation(
    documents: list[AgentInputDocument],
    source_lang: str,
    target_lang: str,
    topic: str | None,
    mode: AgentMode | str,
    providers: list[ModelProvider],
    api_enabled: bool,
    budget_limit: float,
    training_text: str | None = None,
    validation_text: str | None = None,
    store: object | None = None,
    lexicon_store: object | None = None,
    evaluator: TranslationEvaluator | None = None,
    continuation_brief: str | None = None,
    allow_training_upload: bool = False,
    allow_mock_providers: bool = False,
) -> list[AgentRunResult]:
    return [
        run_agent_translation(
            text=document.text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
            mode=mode,
            providers=providers,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
            training_text=training_text,
            validation_text=validation_text,
            input_refs=[document.input_ref],
            store=store,
            lexicon_store=lexicon_store,
            evaluator=evaluator,
            continuation_brief=continuation_brief,
            allow_training_upload=allow_training_upload,
            allow_mock_providers=allow_mock_providers,
        )
        for document in documents
    ]
