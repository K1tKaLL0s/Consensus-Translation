import re

from consensus_translation.topic_taxonomy import (
    topic_audit_categories,
    topic_keyword_map,
)

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = topic_keyword_map()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def extract_domain_signals(text: str) -> dict[str, object]:
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
        "topic_audit_categories": {
            topic: category
            for topic, category in topic_audit_categories().items()
            if topic in tags
        },
    }
