import logging
from difflib import SequenceMatcher
from pathlib import Path

from consensus_translation.config import AppSettings
from consensus_translation.contracts import StageStatus, TranslationJobContract
from consensus_translation.domain_signals import extract_domain_signals
from consensus_translation.engines import LocalEngineA, LocalEngineB
from consensus_translation.evaluation import evaluate_translation
from consensus_translation.lexicon import LexiconRepo, RevisionPayload
from consensus_translation.merging import merge_sentences
from consensus_translation.mdwc import DecisionInput, choose_candidate, score_candidate
from consensus_translation.ops import apply_minimum_log_level, export_audit_payload


LOGGER = logging.getLogger(__name__)


def _safe_translate(
    engine: object,
    engine_name: str,
    text: str,
    source_lang: str,
    target_lang: str,
) -> dict[str, object]:
    try:
        output, conf = engine.translate(text, source_lang, target_lang)
        return {"ok": True, "text": output, "confidence": conf, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "text": None,
            "confidence": 0.0,
            "error": f"{engine_name}: {exc}",
        }


def _diff_ratio(left: str, right: str) -> float:
    left_text = left.strip()
    right_text = right.strip()
    if not left_text and not right_text:
        return 0.0
    similarity = SequenceMatcher(a=left_text, b=right_text).ratio()
    return 1.0 - similarity


def apply_local_revision(
    source_text: str,
    provisional_text: str,
    revised_text: str,
    topic: str | None,
    lexicon_repo: LexiconRepo | None = None,
) -> dict[str, object]:
    repo = lexicon_repo or LexiconRepo()
    effective_topic = topic or "uncategorized"
    ratio = _diff_ratio(provisional_text, revised_text)
    event = repo.apply_revision(
        RevisionPayload(
            topic=effective_topic,
            source=source_text,
            target=revised_text,
            diff_ratio=ratio,
        )
    )

    return {
        "diff_ratio": ratio,
        "special_flag": event.special_flag,
        "update_status": "ok",
        "lexicon_updates": [
            {
                "topic": effective_topic,
                "special_flag": event.special_flag,
            }
        ],
    }


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

    engine_a_result = _safe_translate(engine_a, "engine_a", text, source_lang, target_lang)
    engine_b_result = _safe_translate(engine_b, "engine_b", text, source_lang, target_lang)

    engine_errors: dict[str, str] = {}
    if not bool(engine_a_result["ok"]):
        engine_errors["engine_a"] = str(engine_a_result["error"])
    if not bool(engine_b_result["ok"]):
        engine_errors["engine_b"] = str(engine_b_result["error"])

    if not bool(engine_a_result["ok"]) and not bool(engine_b_result["ok"]):
        contract.stage_status.error_code = "ENGINE_FAILURE"
        contract.stage_status.error_message = str(engine_errors)
        raise RuntimeError("both engines failed")

    if bool(engine_a_result["ok"]) and bool(engine_b_result["ok"]):
        a_text = str(engine_a_result["text"])
        b_text = str(engine_b_result["text"])
        a_conf = float(engine_a_result["confidence"])
        b_conf = float(engine_b_result["confidence"])
        merged = merge_sentences(a_text, b_text, a_conf, b_conf)
        final_text = merged.final_text
        decision_reason = merged.decision_reason
        merge_trace = merged.merge_trace
        LOGGER.debug(
            "engine outputs captured",
            extra={
                "confidence_a": a_conf,
                "confidence_b": b_conf,
            },
        )
    elif bool(engine_a_result["ok"]):
        a_text = str(engine_a_result["text"])
        a_conf = float(engine_a_result["confidence"])
        b_text = ""
        b_conf = 0.0
        final_text = a_text
        decision_reason = "engine-single-survivor-a"
        merge_trace = []
    else:
        a_text = ""
        a_conf = 0.0
        b_text = str(engine_b_result["text"])
        b_conf = float(engine_b_result["confidence"])
        final_text = b_text
        decision_reason = "engine-single-survivor-b"
        merge_trace = []

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

    if bool(engine_a_result["ok"]) and bool(engine_b_result["ok"]):
        winner = choose_candidate(left, right, settings.mdwc_weights)
    elif bool(engine_a_result["ok"]):
        winner = left
    else:
        winner = right
    winner_score = score_candidate(winner, settings.mdwc_weights)
    domain_adjustment = min(0.01 * len(domain_tags), 0.03)
    winner_score = min(winner_score + domain_adjustment, 1.0)
    needs_review = winner_score < 0.55

    if bool(engine_a_result["ok"]) and bool(engine_b_result["ok"]):
        winner_text = a_text if winner is left else b_text
        if not final_text:
            final_text = winner_text
    winner_side = "left" if winner is left else "right"
    overlap_score = 1.0 if a_text == b_text and a_text else 0.5

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
        "decision_reason": decision_reason,
        "domain_tags": domain_tags,
        "decision_trace": f"domain_weight_adjustment: +{domain_adjustment:.3f} tags={','.join(domain_tags) if domain_tags else 'none'}",
        "domain_hits": domain_hits,
        "engine_errors": engine_errors,
        "merge_trace": merge_trace,
        "provisional_text": final_text,
        "checkpoint_used": checkpoint_used,
        "resume_from_stage": resume_value,
        "minimum_log_level": effective_log_level,
        "audit_exported": False,
    }

    if audit_path is not None:
        result["audit_exported"] = True
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
