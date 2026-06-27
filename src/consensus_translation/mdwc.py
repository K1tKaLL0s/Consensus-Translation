from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from consensus_translation.agent_contracts import TranslationCandidate


@dataclass(frozen=True)
class DecisionInput:
    token_score: float
    sentence_score: float
    segment_score: float
    user_prior: float
    locked_term_ok: bool = True


@dataclass(frozen=True)
class MDWCContext:
    topic_match_score: float = 0.0
    user_prior_score: float = 0.0
    validation_coverage: float = 0.0
    budget_spent: float = 0.0
    budget_limit: float = 0.0
    iteration_count: int = 1
    special_marker_count: int = 0
    user_rating_signal: float = 0.0
    provider_historical_rating: float = 0.0
    topic_historical_rating: float = 0.0
    mode_historical_rating: float = 0.0
    low_rating_penalty: float = 0.0
    high_rating_boost: float = 0.0
    mdwc_user_mismatch_rate: float = 0.0


@dataclass(frozen=True)
class MDWCConsensusResult:
    final_text: str
    final_score: float
    confidence_level: str
    accepted_segments: list[str]
    rejected_segments: list[str]
    conflicts: list[str]
    arbitration_reason: str
    requires_human_review: bool
    vote_map: dict[str, int]
    mdwc_scores: dict[str, float]
    winning_provider_id: str
    scoring_dimensions: dict[str, float] = field(default_factory=dict)


def _clamp(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def score_candidate(row: DecisionInput, weights: dict[str, float]) -> float:
    return (
        row.token_score * weights["token"]
        + row.sentence_score * weights["sentence"]
        + row.segment_score * weights["segment"]
        + row.user_prior * weights["user_prior"]
    )


def choose_candidate(
    left: DecisionInput, right: DecisionInput, weights: dict[str, float]
) -> DecisionInput:
    if left.locked_term_ok != right.locked_term_ok:
        return left if left.locked_term_ok else right

    left_score = score_candidate(left, weights)
    right_score = score_candidate(right, weights)
    if left_score >= right_score:
        return left
    return right


def _text_overlap(left: str, right: str) -> float:
    left_value = left.strip()
    right_value = right.strip()
    if not left_value and not right_value:
        return 1.0
    if not left_value or not right_value:
        return 0.0
    return SequenceMatcher(a=left_value, b=right_value).ratio()


def _average_pairwise_overlap(candidates: list[TranslationCandidate]) -> float:
    if len(candidates) < 2:
        return 1.0 if candidates else 0.0
    scores: list[float] = []
    for left_index, left in enumerate(candidates):
        for right in candidates[left_index + 1 :]:
            scores.append(_text_overlap(left.text, right.text))
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _term_hit_score(candidates: list[TranslationCandidate]) -> float:
    if not candidates:
        return 0.0
    hit_values = []
    for candidate in candidates:
        total_hits = sum(
            value for value in candidate.term_hits.values() if isinstance(value, int)
        )
        hit_values.append(min(total_hits / 3.0, 1.0))
    return sum(hit_values) / len(hit_values)


def _budget_score(context: MDWCContext) -> float:
    if context.budget_limit <= 0:
        return 1.0 if context.budget_spent <= 0 else 0.0
    return _clamp(1.0 - (context.budget_spent / context.budget_limit))


def _neutral_rating(value: float) -> float:
    return _clamp(value) if value > 0 else 0.5


def _confidence_level(score: float) -> str:
    if score >= 0.78:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def evaluate_mdwc_consensus(
    candidates: list[TranslationCandidate],
    context: MDWCContext | None = None,
) -> MDWCConsensusResult:
    active_context = context or MDWCContext()
    usable_candidates = [candidate for candidate in candidates if candidate.text.strip()]
    if not usable_candidates:
        return MDWCConsensusResult(
            final_text="",
            final_score=0.0,
            confidence_level="low",
            accepted_segments=[],
            rejected_segments=[],
            conflicts=["no_candidates"],
            arbitration_reason="No provider returned a usable translation candidate.",
            requires_human_review=True,
            vote_map={},
            mdwc_scores={},
            winning_provider_id="",
            scoring_dimensions={},
        )

    vote_counter = Counter(candidate.text for candidate in usable_candidates)
    best_vote_text = max(
        vote_counter,
        key=lambda text: (
            vote_counter[text],
            max(
                candidate.confidence
                for candidate in usable_candidates
                if candidate.text == text
            ),
        ),
    )
    best_vote_count = vote_counter[best_vote_text]
    winning_candidates = [
        candidate for candidate in usable_candidates if candidate.text == best_vote_text
    ]
    winner = max(winning_candidates, key=lambda candidate: candidate.confidence)
    rejected_texts = [
        text for text in sorted(vote_counter) if text != best_vote_text
    ]

    local_candidates = [
        candidate for candidate in usable_candidates if candidate.provider_kind == "local"
    ]
    cloud_candidates = [
        candidate for candidate in usable_candidates if candidate.provider_kind == "cloud"
    ]
    local_confidence = (
        sum(candidate.confidence for candidate in local_candidates) / len(local_candidates)
        if local_candidates
        else 0.0
    )
    cloud_confidence = (
        sum(candidate.confidence for candidate in cloud_candidates) / len(cloud_candidates)
        if cloud_candidates
        else 0.0
    )
    overlap_score = _average_pairwise_overlap(usable_candidates)
    vote_score = best_vote_count / len(usable_candidates)
    term_score = _term_hit_score(usable_candidates)
    special_penalty = min(active_context.special_marker_count * 0.08, 0.32)
    iteration_penalty = max(active_context.iteration_count - 1, 0) * 0.03
    provider_historical_rating = _neutral_rating(active_context.provider_historical_rating)
    topic_historical_rating = _neutral_rating(active_context.topic_historical_rating)
    mode_historical_rating = _neutral_rating(active_context.mode_historical_rating)
    user_rating_signal = _neutral_rating(active_context.user_rating_signal)
    low_rating_penalty = _clamp(active_context.low_rating_penalty)
    high_rating_boost = _clamp(active_context.high_rating_boost)
    mdwc_user_mismatch_rate = _clamp(active_context.mdwc_user_mismatch_rate)
    rating_adjustment = (
        (provider_historical_rating - 0.5) * 0.07
        + (topic_historical_rating - 0.5) * 0.05
        + (mode_historical_rating - 0.5) * 0.03
        + (user_rating_signal - 0.5) * 0.04
        + high_rating_boost
        - low_rating_penalty
        - mdwc_user_mismatch_rate * 0.10
    )

    final_score = _clamp(
        local_confidence * 0.22
        + cloud_confidence * 0.16
        + overlap_score * 0.18
        + vote_score * 0.16
        + term_score * 0.10
        + active_context.topic_match_score * 0.08
        + active_context.user_prior_score * 0.04
        + active_context.validation_coverage * 0.04
        + _budget_score(active_context) * 0.02
        + rating_adjustment
        - special_penalty
        - iteration_penalty
    )
    conflicts: list[str] = []
    if len(vote_counter) > 1:
        conflicts.append("candidate_divergence")
    if overlap_score < 0.55:
        conflicts.append("low_provider_overlap")
    if any(candidate.is_mock for candidate in usable_candidates):
        conflicts.append("mock_provider_present")
    if active_context.special_marker_count > 0:
        conflicts.append("special_marker_penalty")
    if active_context.iteration_count >= 3 and final_score < 0.78:
        conflicts.append("iteration_limit_risk")
    if (
        low_rating_penalty >= 0.15
        or provider_historical_rating < 0.35
        or topic_historical_rating < 0.35
        or mdwc_user_mismatch_rate >= 0.50
    ):
        conflicts.append("historical_user_rating_risk")

    confidence = _confidence_level(final_score)
    requires_review = bool(conflicts) or confidence != "high"
    reasons = [
        f"winner={winner.provider_id}",
        f"votes={best_vote_count}/{len(usable_candidates)}",
        f"overlap={overlap_score:.2f}",
        f"local={local_confidence:.2f}",
    ]
    if cloud_candidates:
        reasons.append(f"cloud={cloud_confidence:.2f}")
    if any(candidate.is_mock for candidate in usable_candidates):
        reasons.append("mock provider output requires human confirmation")
    if conflicts:
        reasons.append("conflicts=" + ",".join(conflicts))

    mdwc_scores = {
        candidate.provider_id: _clamp(
            candidate.confidence * 0.55
            + _text_overlap(candidate.text, best_vote_text) * 0.25
            + (1.0 if candidate.text == best_vote_text else 0.0) * 0.20
        )
        for candidate in usable_candidates
    }
    conflict_penalty = min(len(conflicts) * 0.08, 0.4)
    scoring_dimensions = {
        "adequacy": overlap_score,
        "fluency": sum(candidate.confidence for candidate in usable_candidates) / len(usable_candidates),
        "terminology": term_score,
        "style": vote_score,
        "context": active_context.topic_match_score,
        "providerReliability": provider_historical_rating,
        "userHistoryAlignment": user_rating_signal,
        "specialRiskPenalty": special_penalty,
        "conflictPenalty": conflict_penalty,
        "userRatingSignal": user_rating_signal,
        "providerHistoricalRating": provider_historical_rating,
        "topicHistoricalRating": topic_historical_rating,
        "modeHistoricalRating": mode_historical_rating,
        "lowRatingPenalty": low_rating_penalty,
        "highRatingBoost": high_rating_boost,
        "mdwcUserMismatchRate": mdwc_user_mismatch_rate,
    }

    return MDWCConsensusResult(
        final_text=best_vote_text,
        final_score=final_score,
        confidence_level=confidence,
        accepted_segments=[best_vote_text],
        rejected_segments=rejected_texts,
        conflicts=conflicts,
        arbitration_reason="; ".join(reasons),
        requires_human_review=requires_review,
        vote_map=dict(vote_counter),
        mdwc_scores=mdwc_scores,
        winning_provider_id=winner.provider_id,
        scoring_dimensions=scoring_dimensions,
    )
