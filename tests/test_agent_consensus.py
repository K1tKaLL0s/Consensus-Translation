from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_consensus import (
    align_translation_candidates,
    arbitrate_consensus_result,
    collect_consensus_candidates,
)
from consensus_translation.agent_contracts import TranslationCandidate
from consensus_translation.mdwc import MDWCContext


def test_candidate_layer_adds_segments_reasoning_and_memory_candidates():
    collected = collect_consensus_candidates(
        source_text="Leviathan wakes.",
        provider_candidates=[
            TranslationCandidate(
                provider_id="localProviderA",
                text="Leviathan awakens.",
                confidence=0.72,
                cost=0.0,
                latency=0.11,
                provider_kind="local",
                provider_role="local_a",
            ),
            TranslationCandidate(
                provider_id="localProviderB",
                text="Leviathan wakes.",
                confidence=0.68,
                cost=0.0,
                latency=0.09,
                provider_kind="local",
                provider_role="local_b",
                reasoning="local B preserved tense",
            ),
        ],
        glossary_matches={"Leviathan": "利维坦"},
        translation_memory_matches={"Leviathan wakes.": "利维坦苏醒。"},
    )

    provider_ids = [candidate.provider_id for candidate in collected.candidates]

    assert provider_ids == [
        "localProviderA",
        "localProviderB",
        "glossary",
        "translationMemory",
    ]
    assert all(candidate.segments for candidate in collected.candidates)
    assert all(candidate.reasoning for candidate in collected.candidates)
    assert collected.candidates[0].latency == 0.11
    assert collected.candidates[0].cost == 0.0


def test_alignment_layer_marks_terminology_omission_style_and_entity_conflicts():
    alignment = align_translation_candidates(
        source_text="Leviathan wakes. Alice runs.",
        candidates=[
            TranslationCandidate(
                provider_id="localProviderA",
                text="利维坦苏醒。爱丽丝奔跑。",
                confidence=0.78,
                segments=("利维坦苏醒。", "爱丽丝奔跑。"),
            ),
            TranslationCandidate(
                provider_id="localProviderB",
                text="巨兽醒来。",
                confidence=0.61,
                segments=("巨兽醒来。",),
            ),
        ],
        glossary_matches={"Leviathan": "利维坦"},
    )

    assert len(alignment.aligned_segments) == 2
    first = alignment.aligned_segments[0]
    assert first.conflict_types == ("terminology_conflict", "style_difference")
    assert "localProviderB" in first.provider_text
    assert "entity_difference" in alignment.conflict_summary
    assert "omission" in alignment.conflict_summary


def test_arbitration_layer_exposes_mdwc_scores_conflicts_and_review_gate():
    collected = collect_consensus_candidates(
        source_text="Leviathan wakes.",
        provider_candidates=[
            TranslationCandidate(
                provider_id="localProviderA",
                text="利维坦苏醒。",
                confidence=0.82,
                provider_kind="local",
            ),
            TranslationCandidate(
                provider_id="localProviderB",
                text="巨兽醒来。",
                confidence=0.55,
                provider_kind="local",
            ),
        ],
        glossary_matches={"Leviathan": "利维坦"},
        translation_memory_matches={},
    )
    alignment = align_translation_candidates(
        source_text="Leviathan wakes.",
        candidates=collected.candidates,
        glossary_matches={"Leviathan": "利维坦"},
    )

    decision = arbitrate_consensus_result(
        candidates=collected.candidates,
        alignment=alignment,
        mdwc_context=MDWCContext(
            topic_match_score=0.6,
            provider_historical_rating=0.35,
            topic_historical_rating=0.4,
            low_rating_penalty=0.2,
        ),
    )

    assert decision.final_text == "利维坦苏醒。"
    assert decision.requires_human_review is True
    assert "terminology_conflict" in decision.conflict_points
    assert "providerHistoricalRating" in decision.scoring_dimensions
    assert "lowRatingPenalty" in decision.scoring_dimensions
    assert "terminology_conflict" in decision.arbitration_reason
