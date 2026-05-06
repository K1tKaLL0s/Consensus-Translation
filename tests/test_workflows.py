from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.health import health_report
from consensus_translation.workflows import run_local_job, run_pretrain_job


def test_pretrain_returns_calibration_summary_and_updates():
    result = run_pretrain_job(
        train_text="车站",
        validation_text="列车",
        source_lang="zh",
        target_lang="ja",
        topic="travel",
    )

    assert result["mode"] == "pretrain"
    assert result["calibration_summary"] == "pretrain-complete"
    assert result["validation_text"] == "列车"
    assert result["base_result"]["mode"] == "local"
    assert result["base_result"]["final_text"] == "A::车站"
    assert result["lexicon_updates"] == [{"topic": "travel", "special_flag": False}]


def test_local_job_marks_needs_review_when_scores_low():
    result = run_local_job(
        text="你好",
        source_lang="zh",
        target_lang="ja",
        topic="greeting",
    )

    assert result["mode"] == "local"
    assert result["winner"] in {"left", "right"}
    assert set(result.keys()) == {
        "mode",
        "source_lang",
        "target_lang",
        "topic",
        "winner",
        "final_text",
        "final_score",
        "needs_review",
    }
    assert result["final_text"] == "A::你好"
    assert result["final_score"] == pytest.approx(0.4525)
    assert result["needs_review"] is True


def test_health_report_has_three_levels_and_ok_flags():
    report = health_report()

    assert set(report.keys()) == {"l1_process", "l2_service", "l3_task"}

    assert report["l1_process"]["ok"] is True
    assert isinstance(report["l1_process"]["detail"], str)
    assert report["l1_process"]["detail"]

    assert report["l2_service"]["ok"] is True
    assert isinstance(report["l2_service"]["detail"], str)
    assert report["l2_service"]["detail"]

    assert isinstance(report["l3_task"]["ok"], bool)
    assert isinstance(report["l3_task"]["detail"], str)
    assert report["l3_task"]["detail"]
