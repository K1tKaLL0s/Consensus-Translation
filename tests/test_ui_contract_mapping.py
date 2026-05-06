from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.contracts import TranslationJobContract
from app import PAGE_FIELD_MAP


def test_monitor_page_uses_contract_fields_only():
    contract_fields = set(TranslationJobContract.model_fields.keys())
    monitor_fields = set(PAGE_FIELD_MAP["monitor"])

    assert monitor_fields == contract_fields


def test_mdwc_page_contains_explainability_fields():
    mdwc_fields = set(PAGE_FIELD_MAP["mdwc"])

    assert {
        "token_score",
        "sentence_score",
        "segment_score",
        "user_prior",
        "locked_term_ok",
    }.issubset(mdwc_fields)
