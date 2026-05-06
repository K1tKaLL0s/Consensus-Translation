import math


def compute_final_score(
    mqm_score: float,
    context_score: float,
    frequency_score: float,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> float:
    if alpha < 0 or beta < 0 or gamma < 0:
        raise ValueError("alpha/beta/gamma must be non-negative")
    if not math.isclose(alpha + beta + gamma, 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("alpha/beta/gamma must sum to 1")
    return (mqm_score * alpha) + (context_score * beta) + (frequency_score * gamma)


def select_consensus(
    candidates: list[dict],
    threshold: float,
    kanji_raw: str,
    romaji: str,
) -> dict[str, str | float]:
    if not candidates:
        fallback_winner = romaji if romaji else kanji_raw
        return {
            "status": "fallback",
            "winner": fallback_winner,
            "final": 0.0,
        }

    best = max(candidates, key=lambda candidate: candidate["final"])
    best_final = float(best["final"])

    if best_final >= threshold:
        attempted: list[str] = []
        for candidate in candidates:
            provider = str(candidate.get("provider", "")).strip()
            if provider and provider not in attempted:
                attempted.append(provider)

        winners_provider = str(best.get("provider", "")).strip()
        return {
            "status": "auto_approved",
            "winner": str(best["text"]),
            "final": best_final,
            "provider_breakdown": {
                "attempted": attempted,
                "winners_provider": winners_provider,
            },
        }

    fallback_winner = romaji if romaji else kanji_raw
    return {
        "status": "fallback",
        "winner": fallback_winner,
        "final": best_final,
    }
