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
        "contract": {
            "job_id": "job-123",
            "mode": "local",
            "source_lang": "zh",
            "target_lang": "ja",
            "topic": "travel",
            "stage_status": {
                "current": "review",
                "progress": 0.8,
                "retry_count": 1,
                "error_code": None,
                "error_message": None,
            },
        },
        "weights": {"token": 0.4},
        "token_score": 0.45,
        "sentence_score": 0.45,
        "segment_score": 0.45,
        "user_prior": 0.5,
        "final_score": 0.4525,
        "decision_reason": "left-score-greater-or-equal",
    }

    config = extract_page_data("config", payload)
    monitor = extract_page_data("monitor", payload)
    mdwc = extract_page_data("mdwc", payload)

    assert config["job_id"] == "job-123"
    assert config["source_lang"] == "zh"
    assert config["target_lang"] == "ja"
    assert config["topic"] == "travel"
    assert monitor["stage_status.current"] == "review"
    assert monitor["stage_status.progress"] == 0.8
    assert mdwc["token_score"] == 0.45
    assert mdwc["decision_reason"] == "left-score-greater-or-equal"


def test_all_page_fields_resolve_from_runtime_or_contract_fallback():
    payload = {
        "stage_status": {
            "current": None,
        },
        "contract": {
            "stage_status": {
                "current": "finalize",
                "progress": 1.0,
                "retry_count": 0,
                "error_code": None,
                "error_message": None,
            }
        },
        "final_score": 0.9,
    }

    data = extract_page_data("monitor", payload)

    assert data["stage_status.current"] == "finalize"
    assert data["stage_status.progress"] == 1.0


def test_ui_does_not_expose_phase3_ai_mode_controls():
    forbidden = {"ai_mode", "ai_vote", "ai_iteration", "multi_model"}
    all_fields = {field for fields in PAGE_FIELD_MAP.values() for field in fields}

    assert forbidden.isdisjoint(all_fields)
