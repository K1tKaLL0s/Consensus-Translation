from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.domain_signals import extract_domain_signals


def test_extract_domain_signals_identifies_myth_history_and_science_with_hits():
    text = "The dragon myth from the dynasty was written by an astronomer."

    result = extract_domain_signals(text=text, topic="legend")

    assert result["domain_tags"] == ["history", "myth", "science"]
    assert result["domain_hits"] == {
        "myth": 2,
        "history": 1,
        "science": 1,
    }


def test_extract_domain_signals_is_deterministic_and_bounded_for_unknown_input():
    text = "hello world"

    first = extract_domain_signals(text=text, topic=None)
    second = extract_domain_signals(text=text, topic=None)

    assert first == second
    assert first["domain_tags"] == []
    assert first["domain_hits"] == {"myth": 0, "history": 0, "science": 0}
