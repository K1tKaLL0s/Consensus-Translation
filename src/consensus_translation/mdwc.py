from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionInput:
    token_score: float
    sentence_score: float
    segment_score: float
    user_prior: float
    locked_term_ok: bool = True


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
