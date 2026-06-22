from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_contracts import TranslationCandidate
from consensus_translation.mdwc import (
    DecisionInput,
    MDWCContext,
    choose_candidate,
    evaluate_mdwc_consensus,
    score_candidate,
)


def test_score_candidate_uses_configured_weights():
    row = DecisionInput(
        token_score=0.8,
        sentence_score=0.9,
        segment_score=0.7,
        user_prior=0.3,
    )
    weights = {
        "token": 0.4,
        "sentence": 0.35,
        "segment": 0.2,
        "user_prior": 0.05,
    }

    score = score_candidate(row, weights)

    assert score == 0.79


def test_choose_candidate_prefers_locked_term_even_if_sentence_score_lower():
    left = DecisionInput(
        token_score=0.8,
        sentence_score=0.95,
        segment_score=0.8,
        user_prior=0.5,
        locked_term_ok=False,
    )
    right = DecisionInput(
        token_score=0.4,
        sentence_score=0.2,
        segment_score=0.3,
        user_prior=0.1,
        locked_term_ok=True,
    )
    weights = {
        "token": 0.4,
        "sentence": 0.35,
        "segment": 0.2,
        "user_prior": 0.05,
    }

    winner = choose_candidate(left, right, weights)

    assert winner is right

def test_evaluate_mdwc_consensus_returns_structured_agent_arbitration():
    result = evaluate_mdwc_consensus(
        [
            TranslationCandidate(
                provider_id="localProviderA",
                text="Leviathan awakens.",
                confidence=0.72,
                provider_kind="local",
                provider_role="local_a",
                term_hits={"terms": 1},
            ),
            TranslationCandidate(
                provider_id="localProviderB",
                text="Leviathan wakes.",
                confidence=0.68,
                provider_kind="local",
                provider_role="local_b",
                term_hits={"terms": 1},
            ),
            TranslationCandidate(
                provider_id="mockCloudProvider",
                text="Leviathan awakens.",
                confidence=0.8,
                provider_kind="cloud",
                provider_role="cloud",
                is_mock=True,
                warnings=["mock-provider"],
            ),
        ],
        context=MDWCContext(
            topic_match_score=0.75,
            user_prior_score=0.2,
            validation_coverage=0.0,
            budget_spent=0.0,
            budget_limit=1.0,
            iteration_count=1,
            special_marker_count=0,
        ),
    )

    assert result.final_score > 0.0
    assert result.confidence_level in {"high", "medium", "low"}
    assert result.accepted_segments == ["Leviathan awakens."]
    assert result.rejected_segments == ["Leviathan wakes."]
    assert result.conflicts
    assert result.vote_map["Leviathan awakens."] == 2
    assert result.requires_human_review is True
    assert "mock" in result.arbitration_reason.lower()


def test_mdwc_rating_dimensions_penalize_high_mdwc_user_mismatch():
    baseline = evaluate_mdwc_consensus(
        [
            TranslationCandidate(
                provider_id="local-a",
                text="利维坦苏醒。",
                confidence=0.88,
                provider_kind="local",
            ),
            TranslationCandidate(
                provider_id="local-b",
                text="利维坦苏醒。",
                confidence=0.86,
                provider_kind="local",
            ),
        ],
        context=MDWCContext(provider_historical_rating=0.9, topic_historical_rating=0.9),
    )
    penalized = evaluate_mdwc_consensus(
        [
            TranslationCandidate(
                provider_id="local-a",
                text="利维坦苏醒。",
                confidence=0.88,
                provider_kind="local",
            ),
            TranslationCandidate(
                provider_id="local-b",
                text="利维坦苏醒。",
                confidence=0.86,
                provider_kind="local",
            ),
        ],
        context=MDWCContext(
            provider_historical_rating=0.2,
            topic_historical_rating=0.3,
            mode_historical_rating=0.4,
            low_rating_penalty=0.25,
            mdwc_user_mismatch_rate=0.8,
        ),
    )

    assert penalized.final_score < baseline.final_score
    assert penalized.requires_human_review is True
    assert "historical_user_rating_risk" in penalized.conflicts
    assert penalized.scoring_dimensions["providerHistoricalRating"] == 0.2
    assert penalized.scoring_dimensions["lowRatingPenalty"] == 0.25
    assert penalized.scoring_dimensions["mdwcUserMismatchRate"] == 0.8
