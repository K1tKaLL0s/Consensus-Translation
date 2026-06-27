from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.domain_signals import extract_domain_signals
from consensus_translation.topic_taxonomy import TOPIC_TAXONOMY


def test_extract_domain_signals_identifies_myth_history_and_science_with_hits():
    text = "The dragon myth from the dynasty was written by an astronomer."

    result = extract_domain_signals(text=text)

    assert result["domain_tags"] == ["history", "myth", "science"]
    assert result["domain_hits"] == {
        "myth": 2,
        "history": 1,
        "science": 1,
    }
    assert result["topic_audit_categories"] == {
        "history": "historical_context",
        "myth": "lore",
        "science": "technical_accuracy",
    }


def test_extract_domain_signals_is_deterministic_and_bounded_for_unknown_input():
    text = "hello world"

    first = extract_domain_signals(text=text)
    second = extract_domain_signals(text=text)

    assert first == second
    assert first["domain_tags"] == []
    assert first["domain_hits"] == {"myth": 0, "history": 0, "science": 0}


def test_topic_taxonomy_exposes_mvp_registry_metadata():
    topics = {entry.topic_id: entry for entry in TOPIC_TAXONOMY}

    assert set(topics) == {"history", "myth", "science"}
    assert topics["myth"].risk_level == "high"
    assert "terminology" in topics["science"].provider_hints
