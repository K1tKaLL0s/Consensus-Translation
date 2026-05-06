from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.contracts import StageStatus
import consensus_translation.health as health_module
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
    assert set(result["validation_metrics"].keys()) == {
        "bleu",
        "comet",
        "term_consistency",
    }
    assert isinstance(result["improvement_rate"], float)
    assert isinstance(result["conflict_terms"], list)
    assert isinstance(result["uncategorized_terms"], list)
    assert result["contract"]["stage_status"]["current"] == StageStatus.FINALIZE.value
    assert result["contract"]["stage_status"]["progress"] == 1.0
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
    expected_min_keys = {
        "mode",
        "source_lang",
        "target_lang",
        "topic",
        "winner",
        "final_text",
        "final_score",
        "needs_review",
        "contract",
        "cand_a",
        "cand_b",
        "token_diff",
        "sentence_diff",
        "segment_diff",
        "overlap_score",
        "confidence_a",
        "confidence_b",
        "term_consistency",
        "weights",
        "token_score",
        "sentence_score",
        "segment_score",
        "user_prior",
        "decision_reason",
    }
    assert expected_min_keys.issubset(set(result.keys()))
    assert result["contract"]["stage_status"]["current"] == StageStatus.FINALIZE.value
    assert result["contract"]["stage_status"]["progress"] == 1.0
    assert result["final_text"] == "A::你好"
    assert result["final_score"] == pytest.approx(0.4525)
    assert result["needs_review"] is True


def test_health_report_has_three_levels_and_ok_flags():
    report = health_module.health_report()

    assert set(report.keys()) == {"l1_process", "l2_service", "l3_task"}

    assert isinstance(report["l1_process"]["ok"], bool)
    assert isinstance(report["l1_process"]["detail"], str)
    assert report["l1_process"]["detail"]

    assert isinstance(report["l2_service"]["ok"], bool)
    assert isinstance(report["l2_service"]["detail"], str)
    assert report["l2_service"]["detail"]

    assert isinstance(report["l3_task"]["ok"], bool)
    assert isinstance(report["l3_task"]["detail"], str)
    assert report["l3_task"]["detail"]


def test_health_report_surfaces_l2_failure_detail(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("simulated workflow outage")

    monkeypatch.setattr(health_module, "run_local_job", boom)

    report = health_module.health_report()

    assert report["l2_service"]["ok"] is False
    assert "simulated workflow outage" in report["l2_service"]["detail"]
