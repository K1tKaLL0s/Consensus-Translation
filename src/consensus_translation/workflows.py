import logging
from pathlib import Path

from consensus_translation.config import AppSettings
from consensus_translation.contracts import StageStatus, TranslationJobContract
from consensus_translation.domain_signals import extract_domain_signals
from consensus_translation.engines import LocalEngineA, LocalEngineB
from consensus_translation.evaluation import evaluate_translation
from consensus_translation.lexicon import LexiconRepo, RevisionPayload
from consensus_translation.mdwc import DecisionInput, choose_candidate, score_candidate
from consensus_translation.ops import apply_minimum_log_level, export_audit_payload


LOGGER = logging.getLogger(__name__)


def run_local_job(
    text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
    audit_path: str | Path | None = None,
    resume_from_stage: StageStatus | str | None = None,
) -> dict[str, object]:
    effective_log_level = apply_minimum_log_level(LOGGER)
    LOGGER.info(
        "local workflow started",
        extra={
            "source_lang": source_lang,
            "target_lang": target_lang,
            "topic": topic,
            "minimum_log_level": effective_log_level,
        },
    )

    settings = AppSettings()
    contract = TranslationJobContract.new_job(
        mode="local",
        source_lang=source_lang,
        target_lang=target_lang,
        topic=topic or "uncategorized",
    )

    def update_stage(stage: StageStatus, progress: float) -> None:
        contract.stage_status.current = stage
        contract.stage_status.progress = progress

    checkpoint_used = False
    resume_value: str | None = None
    if resume_from_stage is not None:
        checkpoint_used = True
        if isinstance(resume_from_stage, StageStatus):
            resume_value = resume_from_stage.value
        else:
            resume_value = str(resume_from_stage)
        contract.stage_status.retry_count += 1

    update_stage(StageStatus.INGEST, 0.05)

    engine_a = LocalEngineA()
    engine_b = LocalEngineB()

    update_stage(StageStatus.SEGMENT, 0.2)
    update_stage(StageStatus.ENGINE, 0.45)

    try:
        a_text, a_conf = engine_a.translate(text, source_lang, target_lang)
        b_text, b_conf = engine_b.translate(text, source_lang, target_lang)
        LOGGER.debug(
            "engine outputs captured",
            extra={
                "confidence_a": a_conf,
                "confidence_b": b_conf,
            },
        )
    except Exception as exc:
        contract.stage_status.error_code = "ENGINE_FAILURE"
        contract.stage_status.error_message = str(exc)
        raise

    update_stage(StageStatus.CROSS_CHECK, 0.65)

    domain_signals = extract_domain_signals(text=text)
    domain_tags = domain_signals["domain_tags"]
    domain_hits = domain_signals["domain_hits"]

    left = DecisionInput(
        token_score=a_conf,
        sentence_score=0.45,
        segment_score=0.45,
        user_prior=0.5,
    )
    right = DecisionInput(
        token_score=b_conf,
        sentence_score=0.4,
        segment_score=0.4,
        user_prior=0.5,
    )

    update_stage(StageStatus.MDWC, 0.85)

    winner = choose_candidate(left, right, settings.mdwc_weights)
    winner_score = score_candidate(winner, settings.mdwc_weights)
    domain_adjustment = min(0.01 * len(domain_tags), 0.03)
    winner_score = min(winner_score + domain_adjustment, 1.0)
    needs_review = winner_score < 0.55

    final_text = a_text if winner is left else b_text
    winner_side = "left" if winner is left else "right"
    overlap_score = 1.0 if a_text == b_text else 0.5

    update_stage(StageStatus.REVIEW, 0.95)
    update_stage(StageStatus.FINALIZE, 1.0)

    result: dict[str, object] = {
        "mode": "local",
        "source_lang": source_lang,
        "target_lang": target_lang,
        "topic": topic,
        "winner": winner_side,
        "final_text": final_text,
        "final_score": winner_score,
        "needs_review": needs_review,
        "contract": contract.model_dump(),
        "cand_a": a_text,
        "cand_b": b_text,
        "token_diff": abs(a_conf - b_conf),
        "sentence_diff": abs(left.sentence_score - right.sentence_score),
        "segment_diff": abs(left.segment_score - right.segment_score),
        "overlap_score": overlap_score,
        "confidence_a": a_conf,
        "confidence_b": b_conf,
        "term_consistency": 1.0,
        "weights": settings.mdwc_weights,
        "token_score": winner.token_score,
        "sentence_score": winner.sentence_score,
        "segment_score": winner.segment_score,
        "user_prior": winner.user_prior,
        "decision_reason": "left-score-greater-or-equal" if winner is left else "right-score-greater",
        "domain_tags": domain_tags,
        "decision_trace": f"domain_weight_adjustment: +{domain_adjustment:.3f} tags={','.join(domain_tags) if domain_tags else 'none'}",
        "domain_hits": domain_hits,
        "checkpoint_used": checkpoint_used,
        "resume_from_stage": resume_value,
        "minimum_log_level": effective_log_level,
    }

    if audit_path is not None:
        export_audit_payload(result, audit_path)

    return result


def run_pretrain_job(
    train_text: str,
    validation_text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
) -> dict[str, object]:
    settings = AppSettings()
    contract = TranslationJobContract.new_job(
        mode="pretrain",
        source_lang=source_lang,
        target_lang=target_lang,
        topic=topic or "uncategorized",
    )

    def update_stage(stage: StageStatus, progress: float) -> None:
        contract.stage_status.current = stage
        contract.stage_status.progress = progress

    update_stage(StageStatus.INGEST, 0.1)
    base_result = run_local_job(train_text, source_lang, target_lang, topic)
    update_stage(StageStatus.ENGINE, 0.5)

    repo = LexiconRepo()
    try:
        event = repo.apply_revision(
            RevisionPayload(
                topic=topic,
                source=train_text,
                target=str(base_result["final_text"]),
                diff_ratio=0.5,
            )
        )
    except Exception as exc:
        contract.stage_status.error_code = "LEXICON_WRITE_FAILURE"
        contract.stage_status.error_message = str(exc)
        raise

    update_stage(StageStatus.REVIEW, 0.85)
    validation_metrics = evaluate_translation(
        str(base_result["final_text"]), validation_text
    )
    improvement_rate = max(
        0.0, validation_metrics["overall"] - settings.pretrain_baseline_overall
    )
    update_stage(StageStatus.FINALIZE, 1.0)

    return {
        "mode": "pretrain",
        "base_result": base_result,
        "validation_text": validation_text,
        "calibration_summary": "pretrain-complete",
        "validation_metrics": validation_metrics,
        "improvement_rate": improvement_rate,
        "evaluation_version": settings.evaluation_version,
        "conflict_terms": [],
        "uncategorized_terms": [] if topic else [train_text],
        "contract": contract.model_dump(),
        "lexicon_updates": [
            {
                "topic": topic,
                "special_flag": event.special_flag,
            }
        ],
    }
