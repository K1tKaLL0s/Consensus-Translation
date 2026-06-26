from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicTaxonomyEntry:
    topic_id: str
    keywords: tuple[str, ...]
    audit_category: str
    risk_level: str = "normal"
    provider_hints: tuple[str, ...] = ()


TOPIC_TAXONOMY: tuple[TopicTaxonomyEntry, ...] = (
    TopicTaxonomyEntry(
        topic_id="myth",
        keywords=("myth", "dragon", "legend", "god", "goddess", "ancestor"),
        audit_category="lore",
        risk_level="high",
        provider_hints=("terminology", "lore_consistency"),
    ),
    TopicTaxonomyEntry(
        topic_id="history",
        keywords=("history", "chronicle", "dynasty", "empire", "era", "archive"),
        audit_category="historical_context",
        risk_level="medium",
        provider_hints=("chronology", "proper_nouns"),
    ),
    TopicTaxonomyEntry(
        topic_id="science",
        keywords=("science", "astronomy", "astronomer", "physics", "chemical", "biology"),
        audit_category="technical_accuracy",
        risk_level="medium",
        provider_hints=("terminology", "factual_precision"),
    ),
)


def topic_keyword_map() -> dict[str, tuple[str, ...]]:
    return {entry.topic_id: entry.keywords for entry in TOPIC_TAXONOMY}


def topic_audit_categories() -> dict[str, str]:
    return {entry.topic_id: entry.audit_category for entry in TOPIC_TAXONOMY}
