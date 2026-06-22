from __future__ import annotations

from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from consensus_translation.agent_contracts import ConsensusDecision, TranslationCandidate
from consensus_translation.mdwc import MDWCContext, evaluate_mdwc_consensus


_SEGMENT_PATTERN = re.compile(r"[^。！？.!?\n]+[。！？.!?]?")


@dataclass(frozen=True)
class CandidateLayerResult:
    candidates: list[TranslationCandidate]


@dataclass(frozen=True)
class AlignedSegment:
    index: int
    source_segment: str
    provider_text: dict[str, str]
    conflict_types: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "sourceSegment": self.source_segment,
            "providerText": dict(self.provider_text),
            "conflictTypes": list(self.conflict_types),
        }


@dataclass(frozen=True)
class AlignmentResult:
    aligned_segments: list[AlignedSegment]
    conflict_summary: tuple[str, ...]


def segment_translation_text(text: str) -> tuple[str, ...]:
    segments = tuple(
        match.group(0).strip()
        for match in _SEGMENT_PATTERN.finditer(text)
        if match.group(0).strip()
    )
    if segments:
        return segments
    stripped = text.strip()
    return (stripped,) if stripped else ()


def normalize_translation_candidate(candidate: TranslationCandidate) -> TranslationCandidate:
    segments = candidate.segments or segment_translation_text(candidate.text)
    reasoning = candidate.reasoning or f"{candidate.provider_id} supplied a translation candidate."
    return TranslationCandidate(
        provider_id=candidate.provider_id,
        text=candidate.text,
        confidence=candidate.confidence,
        cost=candidate.cost,
        latency=candidate.latency,
        term_hits=dict(candidate.term_hits),
        warnings=list(candidate.warnings),
        provider_kind=candidate.provider_kind,
        provider_role=candidate.provider_role,
        is_mock=candidate.is_mock,
        reasoning=reasoning,
        segments=segments,
    )


def _memory_translation_from_matches(
    source_text: str,
    matches: dict[str, str],
) -> str:
    translated = source_text
    for source, target in sorted(matches.items(), key=lambda item: len(item[0]), reverse=True):
        if source:
            translated = translated.replace(source, target)
    return translated


def collect_consensus_candidates(
    *,
    source_text: str,
    provider_candidates: list[TranslationCandidate],
    glossary_matches: dict[str, str],
    translation_memory_matches: dict[str, str],
) -> CandidateLayerResult:
    candidates = [
        normalize_translation_candidate(candidate)
        for candidate in provider_candidates
        if candidate.text.strip()
    ]
    if glossary_matches:
        glossary_text = _memory_translation_from_matches(source_text, glossary_matches)
        if glossary_text.strip() and glossary_text != source_text:
            candidates.append(
                normalize_translation_candidate(
                    TranslationCandidate(
                        provider_id="glossary",
                        text=glossary_text,
                        confidence=0.64,
                        cost=0.0,
                        latency=0.0,
                        term_hits={"terms": len(glossary_matches)},
                        provider_kind="memory",
                        provider_role="glossary",
                        reasoning="Confirmed glossary terms were projected as a memory candidate.",
                    )
                )
            )
    memory_text = translation_memory_matches.get(source_text)
    if memory_text:
        candidates.append(
            normalize_translation_candidate(
                TranslationCandidate(
                    provider_id="translationMemory",
                    text=memory_text,
                    confidence=0.78,
                    cost=0.0,
                    latency=0.0,
                    term_hits={"translation_memory": 1},
                    provider_kind="memory",
                    provider_role="translation_memory",
                    reasoning="Exact translation memory match was supplied as a candidate.",
                )
            )
        )
    return CandidateLayerResult(candidates=candidates)


def _overlap(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return SequenceMatcher(a=left, b=right).ratio()


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def align_translation_candidates(
    *,
    source_text: str,
    candidates: list[TranslationCandidate],
    glossary_matches: dict[str, str],
) -> AlignmentResult:
    source_segments = segment_translation_text(source_text)
    candidate_segments = {
        candidate.provider_id: candidate.segments or segment_translation_text(candidate.text)
        for candidate in candidates
    }
    max_segments = max(
        [len(source_segments), *(len(segments) for segments in candidate_segments.values())],
        default=0,
    )
    aligned: list[AlignedSegment] = []
    summary: list[str] = []
    has_source_entities = bool(re.search(r"\b[A-Z][A-Za-z0-9_-]*\b", source_text))

    for index in range(max_segments):
        source_segment = source_segments[index] if index < len(source_segments) else ""
        provider_text = {
            provider_id: segments[index] if index < len(segments) else ""
            for provider_id, segments in candidate_segments.items()
        }
        non_empty_text = [text for text in provider_text.values() if text.strip()]
        conflicts: list[str] = []
        if any(not text.strip() for text in provider_text.values()) and non_empty_text:
            _append_unique(conflicts, "omission")
            _append_unique(summary, "omission")
        for source_term, target_term in glossary_matches.items():
            if source_term and source_term in source_segment:
                missing = [
                    provider_id
                    for provider_id, text in provider_text.items()
                    if text.strip() and target_term and target_term not in text
                ]
                if missing:
                    _append_unique(conflicts, "terminology_conflict")
                    _append_unique(summary, "terminology_conflict")
                    if has_source_entities:
                        _append_unique(summary, "entity_difference")
        if len(set(non_empty_text)) > 1:
            overlaps = [
                _overlap(left, right)
                for left_index, left in enumerate(non_empty_text)
                for right in non_empty_text[left_index + 1 :]
            ]
            if overlaps and min(overlaps) < 0.72:
                _append_unique(conflicts, "style_difference")
                _append_unique(summary, "style_difference")
        aligned.append(
            AlignedSegment(
                index=index,
                source_segment=source_segment,
                provider_text=provider_text,
                conflict_types=tuple(conflicts),
            )
        )

    if any(len(segments) > len(source_segments) for segments in candidate_segments.values()):
        _append_unique(summary, "addition")
    return AlignmentResult(aligned_segments=aligned, conflict_summary=tuple(summary))


def arbitrate_consensus_result(
    *,
    candidates: list[TranslationCandidate],
    alignment: AlignmentResult,
    mdwc_context: MDWCContext | None = None,
) -> ConsensusDecision:
    mdwc_result = evaluate_mdwc_consensus(candidates, context=mdwc_context)
    conflict_points = list(mdwc_result.conflicts)
    for conflict in alignment.conflict_summary:
        _append_unique(conflict_points, conflict)
    requires_review = mdwc_result.requires_human_review or bool(alignment.conflict_summary)
    alignment_reason = (
        "alignment_conflicts=" + ",".join(alignment.conflict_summary)
        if alignment.conflict_summary
        else "alignment_conflicts=none"
    )
    return ConsensusDecision(
        final_text=mdwc_result.final_text,
        final_score=mdwc_result.final_score,
        vote_map=mdwc_result.vote_map,
        mdwc_scores=mdwc_result.mdwc_scores,
        conflict_points=conflict_points,
        decision_reason=f"mdwc:{mdwc_result.winning_provider_id}",
        confidence_level=mdwc_result.confidence_level,
        accepted_segments=mdwc_result.accepted_segments,
        rejected_segments=mdwc_result.rejected_segments,
        arbitration_reason=f"{mdwc_result.arbitration_reason}; {alignment_reason}",
        requires_human_review=requires_review,
        aligned_segments=[segment.to_dict() for segment in alignment.aligned_segments],
        scoring_dimensions=dict(mdwc_result.scoring_dimensions),
    )
