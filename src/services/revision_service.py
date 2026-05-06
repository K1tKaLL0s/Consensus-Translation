from difflib import SequenceMatcher


def classify_revision(
    original_text: str,
    revised_text: str,
    special_threshold: float = 0.35,
) -> dict[str, object]:
    if not 0.0 <= special_threshold <= 1.0:
        raise ValueError("special_threshold must be between 0.0 and 1.0")

    original_terms = original_text.split()
    revised_terms = revised_text.split()

    matcher = SequenceMatcher(a=original_terms, b=revised_terms)
    similarity_ratio = matcher.ratio()
    change_ratio = 1.0 - similarity_ratio

    changed_terms = sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    )

    if change_ratio > special_threshold:
        normal_terms = []
        special_terms = revised_terms
    else:
        normal_terms = revised_terms
        special_terms = []

    return {
        "change_ratio": change_ratio,
        "normal_terms": normal_terms,
        "special_terms": special_terms,
        "diff_summary": {
            "original_length": len(original_terms),
            "revised_length": len(revised_terms),
            "changed_terms": changed_terms,
        },
    }
