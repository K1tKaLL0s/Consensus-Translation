import re


DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "myth": (
        "myth",
        "dragon",
        "legend",
        "god",
        "goddess",
        "ancestor",
    ),
    "history": (
        "history",
        "chronicle",
        "dynasty",
        "empire",
        "era",
        "archive",
    ),
    "science": (
        "science",
        "astronomy",
        "astronomer",
        "physics",
        "chemical",
        "biology",
    ),
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def extract_domain_signals(text: str, topic: str | None) -> dict[str, object]:
    combined_tokens = _tokenize(text)

    hits: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        keyword_set = set(keywords)
        count = sum(1 for token in combined_tokens if token in keyword_set)
        hits[domain] = min(count, 3)

    tags = [domain for domain in sorted(hits.keys()) if hits[domain] > 0]
    return {
        "domain_tags": tags,
        "domain_hits": hits,
    }
