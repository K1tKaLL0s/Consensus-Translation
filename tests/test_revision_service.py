from src.services.revision_service import classify_revision


def test_classify_revision_marks_special_when_ratio_over_threshold() -> None:
    result = classify_revision(
        original_text="alpha beta gamma",
        revised_text="new text with completely different words",
        special_threshold=0.35,
    )

    assert result["change_ratio"] > 0.35
    assert result["normal_terms"] == []
    assert result["special_terms"] == [
        "new",
        "text",
        "with",
        "completely",
        "different",
        "words",
    ]
    assert result["diff_summary"] == {
        "original_length": 3,
        "revised_length": 6,
        "changed_terms": 6,
    }


def test_classify_revision_returns_normal_terms_when_small_change() -> None:
    result = classify_revision(
        original_text="alpha beta gamma",
        revised_text="alpha beta delta",
        special_threshold=0.35,
    )

    assert result["change_ratio"] < 0.35
    assert result["normal_terms"] == ["alpha", "beta", "delta"]
    assert result["special_terms"] == []
    assert result["diff_summary"] == {
        "original_length": 3,
        "revised_length": 3,
        "changed_terms": 1,
    }


def test_classify_revision_counts_deletions_in_changed_terms() -> None:
    result = classify_revision(
        original_text="alpha beta gamma",
        revised_text="alpha",
        special_threshold=1.0,
    )

    assert result["diff_summary"] == {
        "original_length": 3,
        "revised_length": 1,
        "changed_terms": 2,
    }


def test_classify_revision_treats_equal_threshold_as_non_special() -> None:
    result = classify_revision(
        original_text="alpha beta",
        revised_text="alpha gamma",
        special_threshold=0.5,
    )

    assert result["change_ratio"] == 0.5
    assert result["normal_terms"] == ["alpha", "gamma"]
    assert result["special_terms"] == []


def test_classify_revision_handles_empty_text() -> None:
    result = classify_revision(original_text="", revised_text="")

    assert result["change_ratio"] == 0.0
    assert result["normal_terms"] == []
    assert result["special_terms"] == []
    assert result["diff_summary"] == {
        "original_length": 0,
        "revised_length": 0,
        "changed_terms": 0,
    }


def test_classify_revision_rejects_threshold_below_zero() -> None:
    try:
        classify_revision(original_text="alpha", revised_text="beta", special_threshold=-0.01)
        assert False, "Expected ValueError for threshold below zero"
    except ValueError:
        pass


def test_classify_revision_rejects_threshold_above_one() -> None:
    try:
        classify_revision(original_text="alpha", revised_text="beta", special_threshold=1.01)
        assert False, "Expected ValueError for threshold above one"
    except ValueError:
        pass
