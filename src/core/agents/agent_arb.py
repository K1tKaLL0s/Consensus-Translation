def compute_final_score(
    mqm_score: float,
    context_score: float,
    frequency_score: float,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> float:
    return (mqm_score * alpha) + (context_score * beta) + (frequency_score * gamma)


def select_consensus(
    candidates: list[dict],
    threshold: float,
    kanji_raw: str,
    romaji: str,
) -> dict[str, str | float]:
    best = max(candidates, key=lambda candidate: candidate["final"])
    best_final = float(best["final"])

    if best_final >= threshold:
        return {
            "status": "auto_approved",
            "winner": str(best["text"]),
            "final": best_final,
        }

    fallback_winner = romaji if romaji else kanji_raw
    return {
        "status": "fallback",
        "winner": fallback_winner,
        "final": best_final,
    }
