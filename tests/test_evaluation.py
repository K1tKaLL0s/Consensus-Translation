from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.evaluation import evaluate_translation


def test_evaluate_translation_is_deterministic_with_expected_keys():
    candidate = "train station"
    reference = "station"

    first = evaluate_translation(candidate, reference)
    second = evaluate_translation(candidate, reference)

    assert first == second
    assert set(first.keys()) == {
        "term_consistency",
        "length_ratio",
        "edit_similarity",
        "overall",
    }
    assert 0.0 <= first["term_consistency"] <= 1.0
    assert 0.0 <= first["length_ratio"] <= 1.0
    assert 0.0 <= first["edit_similarity"] <= 1.0
    assert first["overall"] == (
        first["term_consistency"] + first["length_ratio"] + first["edit_similarity"]
    ) / 3.0


def test_evaluate_translation_returns_safe_zero_metrics_for_empty_reference():
    metrics = evaluate_translation("candidate", "")

    assert metrics == {
        "term_consistency": 0.0,
        "length_ratio": 0.0,
        "edit_similarity": 0.0,
        "overall": 0.0,
    }
