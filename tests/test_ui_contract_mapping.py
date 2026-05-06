from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from app import PAGE_FIELD_MAP


def test_monitor_page_uses_plan_defined_status_fields():
    assert PAGE_FIELD_MAP["monitor"] == [
        "stage_status.current",
        "stage_status.progress",
        "stage_status.retry_count",
        "stage_status.error_code",
        "stage_status.error_message",
    ]


def test_mdwc_page_contains_plan_defined_subset():
    mdwc_fields = set(PAGE_FIELD_MAP["mdwc"])

    assert {
        "weights",
        "token_score",
        "sentence_score",
        "segment_score",
        "user_prior",
        "final_score",
        "decision_reason",
    }.issubset(mdwc_fields)
