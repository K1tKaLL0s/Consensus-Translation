from consensus_translation.config import AppSettings
from consensus_translation.engines import LocalEngineA, LocalEngineB
from consensus_translation.lexicon import LexiconRepo, RevisionPayload
from consensus_translation.mdwc import DecisionInput, choose_candidate, score_candidate


def run_local_job(
    text: str, source_lang: str, target_lang: str, topic: str | None
) -> dict[str, object]:
    settings = AppSettings()

    engine_a = LocalEngineA()
    engine_b = LocalEngineB()

    a_text, a_conf = engine_a.translate(text)
    b_text, b_conf = engine_b.translate(text)

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

    winner = choose_candidate(left, right, settings.mdwc_weights)
    winner_score = score_candidate(winner, settings.mdwc_weights)
    needs_review = winner_score < 0.55

    final_text = a_text if winner is left else b_text

    return {
        "mode": "local",
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "topic": topic,
        "left_candidate": a_text,
        "right_candidate": b_text,
        "final_text": final_text,
        "final_score": winner_score,
        "needs_review": needs_review,
    }


def run_pretrain_job(
    train_text: str,
    validation_text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
) -> dict[str, object]:
    base_result = run_local_job(train_text, source_lang, target_lang, topic)

    repo = LexiconRepo()
    event = repo.apply_revision(
        RevisionPayload(
            topic=topic,
            source=train_text,
            target=str(base_result["final_text"]),
            diff_ratio=0.5,
        )
    )

    return {
        "mode": "pretrain",
        "base_result": base_result,
        "validation_text": validation_text,
        "calibration_summary": "pretrain-complete",
        "lexicon_updates": [
            {
                "topic": topic,
                "special_flag": event.special_flag,
            }
        ],
    }
