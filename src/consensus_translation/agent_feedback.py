from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Iterable


LOW_RATING_THRESHOLD = 2
HIGH_RATING_THRESHOLD = 4
MIN_RATING = 1
MAX_RATING = 5


def hash_translation_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _float_value(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _provider_ids(snapshot: Iterable[dict[str, object]]) -> tuple[str, ...]:
    ids: list[str] = []
    for item in snapshot:
        provider_id = str(item.get("providerId", item.get("provider_id", ""))).strip()
        if provider_id:
            ids.append(provider_id)
    return tuple(ids)


@dataclass(frozen=True)
class TranslationRatingSubmission:
    task_id: str
    workflow_run_id: str
    mode: str
    source_language: str
    target_language: str
    topic: str
    rating: int
    issue_tags: tuple[str, ...] = ()
    dimension_scores: dict[str, float] = field(default_factory=dict)
    comment: str = ""
    mdwc_snapshot: dict[str, object] = field(default_factory=dict)
    provider_snapshot: list[dict[str, object]] = field(default_factory=list)
    source_text: str = ""
    final_translation: str = ""

    def __post_init__(self) -> None:
        if self.rating < MIN_RATING or self.rating > MAX_RATING:
            raise ValueError("rating must be between 1 and 5")


@dataclass(frozen=True)
class TranslationRating:
    id: int
    task_id: str
    workflow_run_id: str
    mode: str
    source_language: str
    target_language: str
    topic: str
    rating: int
    issue_tags: tuple[str, ...]
    dimension_scores: dict[str, float]
    comment: str
    mdwc_snapshot: dict[str, object]
    provider_snapshot: tuple[dict[str, object], ...]
    source_text_hash: str
    final_translation_hash: str
    created_at: str

    @classmethod
    def from_submission(
        cls,
        submission: TranslationRatingSubmission,
        *,
        rating_id: int = 0,
        created_at: str | None = None,
    ) -> "TranslationRating":
        return cls(
            id=rating_id,
            task_id=submission.task_id,
            workflow_run_id=submission.workflow_run_id,
            mode=submission.mode,
            source_language=submission.source_language,
            target_language=submission.target_language,
            topic=submission.topic or "uncategorized",
            rating=submission.rating,
            issue_tags=tuple(tag for tag in submission.issue_tags if tag),
            dimension_scores=dict(submission.dimension_scores),
            comment=submission.comment,
            mdwc_snapshot=dict(submission.mdwc_snapshot),
            provider_snapshot=tuple(dict(item) for item in submission.provider_snapshot),
            source_text_hash=hash_translation_text(submission.source_text),
            final_translation_hash=hash_translation_text(submission.final_translation),
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
        )

    @property
    def provider_ids(self) -> tuple[str, ...]:
        return _provider_ids(self.provider_snapshot)

    def to_spec_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "taskId": self.task_id,
            "workflowRunId": self.workflow_run_id,
            "mode": self.mode,
            "sourceLanguage": self.source_language,
            "targetLanguage": self.target_language,
            "topic": self.topic,
            "rating": self.rating,
            "issueTags": list(self.issue_tags),
            "dimensionScores": dict(self.dimension_scores),
            "comment": self.comment,
            "mdwcSnapshot": dict(self.mdwc_snapshot),
            "providerSnapshot": [dict(item) for item in self.provider_snapshot],
            "sourceTextHash": self.source_text_hash,
            "finalTranslationHash": self.final_translation_hash,
            "createdAt": self.created_at,
        }


@dataclass(frozen=True)
class RatingSignalSummary:
    sample_count: int = 0
    topic_average_rating: float = 0.0
    language_pair_average_rating: float = 0.0
    provider_average_rating: float = 0.0
    mode_average_rating: float = 0.0
    recent_low_rating_count: int = 0
    terminology_issue_ratio: float = 0.0
    style_issue_ratio: float = 0.0
    lore_issue_ratio: float = 0.0
    mdwc_user_mismatch_rate: float = 0.0
    low_rating_penalty: float = 0.0
    high_rating_boost: float = 0.0

    @property
    def user_rating_signal(self) -> float:
        if self.sample_count <= 0:
            return 0.0
        values = [
            value
            for value in (
                self.topic_average_rating,
                self.language_pair_average_rating,
                self.provider_average_rating,
                self.mode_average_rating,
            )
            if value > 0
        ]
        if not values:
            return 0.0
        return sum(values) / len(values) / MAX_RATING


def rating_summary_from_records(
    records: list[TranslationRating],
    *,
    topic: str,
    source_language: str,
    target_language: str,
    mode: str,
    provider_ids: tuple[str, ...] = (),
) -> RatingSignalSummary:
    if not records:
        return RatingSignalSummary()

    normalized_topic = topic or "uncategorized"
    provider_id_set = set(provider_ids)

    topic_records = [record for record in records if record.topic == normalized_topic]
    language_records = [
        record
        for record in records
        if record.source_language == source_language
        and record.target_language == target_language
    ]
    mode_records = [record for record in records if record.mode == mode]
    provider_records = [
        record
        for record in records
        if not provider_id_set or provider_id_set.intersection(record.provider_ids)
    ]
    relevant_records = [
        record
        for record in records
        if record.topic == normalized_topic
        and record.source_language == source_language
        and record.target_language == target_language
        and record.mode == mode
        and (not provider_id_set or provider_id_set.intersection(record.provider_ids))
    ]
    if not relevant_records:
        relevant_records = topic_records or language_records or provider_records

    def average(items: list[TranslationRating]) -> float:
        if not items:
            return 0.0
        return sum(item.rating for item in items) / len(items)

    sample_count = len(relevant_records)
    low_count = sum(1 for item in relevant_records if item.rating <= LOW_RATING_THRESHOLD)
    high_count = sum(1 for item in relevant_records if item.rating >= HIGH_RATING_THRESHOLD)

    def issue_ratio(*tags: str) -> float:
        if not relevant_records:
            return 0.0
        tag_set = set(tags)
        return sum(
            1 for item in relevant_records if tag_set.intersection(item.issue_tags)
        ) / len(relevant_records)

    mismatch_count = 0
    for item in relevant_records:
        mdwc_score = _float_value(
            item.mdwc_snapshot.get("finalScore", item.mdwc_snapshot.get("final_score")),
        )
        if mdwc_score >= 0.75 and item.rating <= LOW_RATING_THRESHOLD:
            mismatch_count += 1
    mismatch_rate = mismatch_count / sample_count if sample_count else 0.0
    low_ratio = low_count / sample_count if sample_count else 0.0
    high_ratio = high_count / sample_count if sample_count else 0.0

    topic_average = average(topic_records)
    penalty_floor = max(0.0, (2.8 - (topic_average or MAX_RATING)) / MAX_RATING)
    return RatingSignalSummary(
        sample_count=sample_count,
        topic_average_rating=topic_average,
        language_pair_average_rating=average(language_records),
        provider_average_rating=average(provider_records),
        mode_average_rating=average(mode_records),
        recent_low_rating_count=low_count,
        terminology_issue_ratio=issue_ratio("terminology_error"),
        style_issue_ratio=issue_ratio("style_mismatch", "tone_mismatch"),
        lore_issue_ratio=issue_ratio("lore_error"),
        mdwc_user_mismatch_rate=mismatch_rate,
        low_rating_penalty=min(low_ratio * 0.22 + penalty_floor, 0.45),
        high_rating_boost=min(high_ratio * 0.08, 0.12),
    )
