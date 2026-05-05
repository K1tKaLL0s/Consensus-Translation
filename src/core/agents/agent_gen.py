def generate_candidates(term: str) -> dict[str, str]:
    clean = term.strip()
    return {
        "gen_a": clean,
        "gen_b": f"{clean}の候補B",
        "gen_c": f"{clean}の候補C",
    }
