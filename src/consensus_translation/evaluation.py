from difflib import SequenceMatcher


def evaluate_translation(candidate: str, reference: str) -> dict[str, float]:
    if not reference:
        return {
            "term_consistency": 0.0,
            "length_ratio": 0.0,
            "edit_similarity": 0.0,
            "overall": 0.0,
        }

    candidate_tokens = set(candidate.split())
    reference_tokens = set(reference.split())
    if reference_tokens:
        term_consistency = len(candidate_tokens & reference_tokens) / len(reference_tokens)
    else:
        term_consistency = 0.0

    candidate_len = len(candidate)
    reference_len = len(reference)
    length_ratio = min(candidate_len, reference_len) / max(candidate_len, reference_len)

    edit_similarity = SequenceMatcher(a=candidate, b=reference).ratio()

    overall = (term_consistency + length_ratio + edit_similarity) / 3.0
    return {
        "term_consistency": term_consistency,
        "length_ratio": length_ratio,
        "edit_similarity": edit_similarity,
        "overall": overall,
    }
