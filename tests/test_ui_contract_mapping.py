from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from app import PAGE_FIELD_MAP, extract_page_data, resolve_dot_path


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


def test_resolve_dot_path_returns_nested_value_and_none_for_missing():
    payload = {
        "stage_status": {
            "current": "finalize",
            "progress": 1.0,
        }
    }

    assert resolve_dot_path(payload, "stage_status.current") == "finalize"
    assert resolve_dot_path(payload, "stage_status.progress") == 1.0
    assert resolve_dot_path(payload, "stage_status.error_code") is None


def test_extract_page_data_maps_runtime_payload_values():
    payload = {
        "stage_status": {
            "current": "review",
            "progress": 0.8,
            "retry_count": 1,
            "error_code": None,
            "error_message": None,
        },
        "weights": {"token": 0.4},
        "token_score": 0.45,
        "sentence_score": 0.45,
        "segment_score": 0.45,
        "user_prior": 0.5,
        "final_score": 0.4525,
        "decision_reason": "left-score-greater-or-equal",
    }

    monitor = extract_page_data("monitor", payload)
    mdwc = extract_page_data("mdwc", payload)

    assert monitor["stage_status.current"] == "review"
    assert monitor["stage_status.progress"] == 0.8
    assert mdwc["token_score"] == 0.45
    assert mdwc["decision_reason"] == "left-score-greater-or-equal"
