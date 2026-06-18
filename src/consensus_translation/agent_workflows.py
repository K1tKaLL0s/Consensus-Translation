from __future__ import annotations

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
from consensus_translation.agent_evaluators import (
    DeterministicTranslationEvaluator,
    EvaluationRequest,
    TranslationEvaluator,
)
from consensus_translation.agent_inputs import AgentInputDocument
from consensus_translation.agent_meta_policy import MetaPolicyAgent
from consensus_translation.agent_providers import ModelProvider, ProviderRequest
from consensus_translation.domain_signals import extract_domain_signals


VALIDATION_PASS_THRESHOLD = 0.75


def _empty_decision(reason: str) -> ConsensusDecision:
    return ConsensusDecision(
        final_text="",
        final_score=0.0,
        vote_map={},
        mdwc_scores={},
        conflict_points=[],
        decision_reason=reason,
    )


def _decide(candidates: list[TranslationCandidate]) -> ConsensusDecision:
    if not candidates:
        return _empty_decision("no-candidates")

    winner = max(candidates, key=lambda candidate: candidate.confidence)
    unique_texts = {candidate.text for candidate in candidates}
    conflict_points = ["candidate_divergence"] if len(unique_texts) > 1 else []
    return ConsensusDecision(
        final_text=winner.text,
        final_score=winner.confidence,
        vote_map={candidate.provider_id: 1 for candidate in candidates},
        mdwc_scores={
            candidate.provider_id: candidate.confidence for candidate in candidates
        },
        conflict_points=conflict_points,
        decision_reason=f"highest-confidence:{winner.provider_id}",
    )


def _build_memory_proposals(
    text: str,
    topic: str | None,
    decision: ConsensusDecision,
    policy: ModePolicy,
) -> list[LexiconUpdateProposal]:
    if not decision.final_text:
        return []
    return [
        LexiconUpdateProposal(
            topic=topic or "uncategorized",
            layer="terms",
            source=text,
            target=decision.final_text,
            rationale="agent-final-candidate",
            confidence=decision.final_score,
            requires_user_confirm=policy.human_gate_required,
        )
    ]


def _empty_lexicon_matches() -> dict[str, dict[str, str]]:
    return {"terms": {}, "phrases": {}, "style_rules": {}}


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
) -> AgentRunResult:
    requested_mode = AgentMode(mode)
    effective_mode = requested_mode
    trace: list[str] = []

    if requested_mode == AgentMode.SELF_DECISION:
        meta_decision = MetaPolicyAgent().select_mode(
            training_text=training_text,
            validation_text=validation_text,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
        )
        effective_mode = meta_decision.selected_mode
        trace.append(f"meta_policy:selected_mode={effective_mode.value}")
        trace.append(f"meta_policy:reason={meta_decision.reason}")
        trace.append(
            f"meta_policy:validation_coverage={meta_decision.validation_coverage:.6f}"
        )

    policy = policy_for_mode(effective_mode, api_enabled, budget_limit)
    if policy.validation_required and (not training_text or not validation_text):
        raise ValueError("self_iterative mode requires training_text and validation_text")

    contract = AgentRunContract.new_run(
        mode=requested_mode,
        input_refs=input_refs or ["inline:text"],
        provider_ids=[provider.provider_id for provider in providers],
        policy=policy,
    )
    contract.trace.extend(trace)
    domain_signals = extract_domain_signals(text)
    if domain_signals["domain_tags"]:
        contract.trace.append(
            "domain_tags:" + ",".join(str(tag) for tag in domain_signals["domain_tags"])
        )
    active_lexicon_store = lexicon_store or store
    lexicon_matches = _collect_lexicon_matches(active_lexicon_store, topic, text)
    if any(lexicon_matches[layer] for layer in lexicon_matches):
        contract.trace.append(
            "lexicon_hits:"
            + ",".join(
                f"{layer}={len(lexicon_matches[layer])}"
                for layer in ("terms", "phrases", "style_rules")
            )
        )

    candidates: list[TranslationCandidate] = []
    decision = _empty_decision("not-run")
    stop_for_budget = False
    validation_passed = not policy.validation_required
    active_evaluator: TranslationEvaluator = evaluator or DeterministicTranslationEvaluator()

    for round_index in range(1, policy.max_rounds + 1):
        contract.trace.append(f"round:{round_index}")
        for provider in providers:
            if provider.requires_api and not policy.api_enabled:
                contract.trace.append(f"provider_skipped:{provider.provider_id}:api_disabled")
                continue

            next_cost = contract.budget["spent"] + provider.estimated_cost
            if next_cost > policy.budget_limit:
                contract.trace.append(f"budget_exceeded:{provider.provider_id}")
                contract.status = AgentRunStatus.BUDGET_EXCEEDED
                stop_for_budget = True
                break

            candidate = provider.translate(
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
            )
            contract.budget["spent"] += candidate.cost
            candidates.append(candidate)

        decision = _decide(candidates)
        if policy.validation_required:
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

    proposals = _build_memory_proposals(text, topic, decision, policy)

    if contract.status != AgentRunStatus.BUDGET_EXCEEDED:
        if not candidates:
            contract.status = AgentRunStatus.NEEDS_REVIEW
        elif policy.validation_required and not validation_passed:
            contract.status = AgentRunStatus.NEEDS_REVIEW
            contract.trace.append("validation_failed:max_rounds")
        elif policy.human_gate_required:
            contract.status = AgentRunStatus.AWAITING_HUMAN_CONFIRMATION
            contract.trace.append("human_gate:required")
        else:
            contract.status = AgentRunStatus.FINALIZED

    result = AgentRunResult(
        contract=contract,
        candidates=candidates,
        decision=decision,
        lexicon_proposals=proposals,
    )
    if store is not None:
        store.record_result(result)
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
        )
        for document in documents
    ]
