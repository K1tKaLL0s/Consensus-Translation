from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.mdwc import DecisionInput, choose_candidate, score_candidate


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
