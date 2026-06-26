from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from consensus_translation.help_content import HelpIndex


def test_help_search_finds_textractor_guidance():
    index = HelpIndex.load_default()

    results = index.search("Textractor")

    assert results
    assert results[0].topic_id == "connectors"
    assert "Textractor" in results[0].markdown


def test_help_index_loads_release_topics():
    index = HelpIndex.load_default()

    assert index.topic_ids() == [
        "quick-start",
        "connectors",
        "providers",
        "runtime-troubleshooting",
        "privacy-and-licenses",
    ]
