import json
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


def test_pretrain_returns_calibration_summary_and_updates(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("station", 0.8),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("train station", 0.6),
    )

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
    assert result["base_result"]["final_text"] == "station"
    assert set(result["validation_metrics"].keys()) == {
        "term_consistency",
        "length_ratio",
        "edit_similarity",
        "overall",
    }
    assert 0.0 <= result["validation_metrics"]["overall"] <= 1.0
    assert isinstance(result["improvement_rate"], float)
    assert isinstance(result["conflict_terms"], list)
    assert isinstance(result["uncategorized_terms"], list)
    assert result["contract"]["stage_status"]["current"] == StageStatus.FINALIZE.value
    assert result["contract"]["stage_status"]["progress"] == 1.0
    assert result["lexicon_updates"] == [{"topic": "travel", "special_flag": False}]


def test_local_job_marks_needs_review_when_scores_low(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("hello", 0.45),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("hi", 0.4),
    )

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
    assert result["final_text"] == "hello"
    assert result["final_score"] == pytest.approx(0.4525)
    assert result["needs_review"] is True


def test_local_job_applies_domain_adjustment_and_reports_trace_and_hits(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("ancestor chronicle", 0.7),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("ancestor log", 0.69),
    )

    result = run_local_job(
        text="A myth chronicle mentions the ancestor.",
        source_lang="en",
        target_lang="ja",
        topic="history",
    )

    assert result["domain_tags"] == ["history", "myth"]
    assert result["domain_hits"] == {"myth": 2, "history": 1, "science": 0}
    assert result["decision_trace"] == "domain_weight_adjustment: +0.020 tags=history,myth"
    assert result["final_score"] == pytest.approx(0.5725)


def test_local_job_with_no_domain_signals_has_zero_adjustment_trace(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("hello", 0.45),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("hi", 0.4),
    )

    result = run_local_job(
        text="你好",
        source_lang="zh",
        target_lang="ja",
        topic="greeting",
    )

    assert result["domain_tags"] == []
    assert result["domain_hits"] == {"myth": 0, "history": 0, "science": 0}
    assert result["decision_trace"] == "domain_weight_adjustment: +0.000 tags=none"
    assert result["final_score"] == pytest.approx(0.4525)


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


def test_local_job_exports_audit_json_when_path_is_provided(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("station", 0.8),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("train station", 0.6),
    )

    audit_path = tmp_path / "audit" / "local-job.json"
    result = run_local_job(
        text="车站",
        source_lang="zh",
        target_lang="ja",
        topic="travel",
        audit_path=audit_path,
    )

    assert audit_path.exists()
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload["final_text"] == result["final_text"]
    assert audit_payload["winner"] == result["winner"]
    assert audit_payload["minimum_log_level"] == "INFO"
    assert audit_payload["contract"]["stage_status"]["current"] == StageStatus.FINALIZE.value


def test_local_job_supports_resume_from_stage_and_increments_retry(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("station", 0.8),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("train station", 0.6),
    )

    result = run_local_job(
        text="车站",
        source_lang="zh",
        target_lang="ja",
        topic="travel",
        resume_from_stage=StageStatus.ENGINE,
    )

    assert result["checkpoint_used"] is True
    assert result["resume_from_stage"] == StageStatus.ENGINE.value
    assert result["contract"]["stage_status"]["retry_count"] == 1


def test_local_job_audit_uses_minimum_log_level_env(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("station", 0.8),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("train station", 0.6),
    )
    monkeypatch.setenv("CT_MIN_LOG_LEVEL", "warning")

    audit_path = tmp_path / "audit" / "minimum-level.json"
    run_local_job(
        text="车站",
        source_lang="zh",
        target_lang="ja",
        topic="travel",
        audit_path=audit_path,
    )

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload["minimum_log_level"] == "WARNING"


def test_local_job_runtime_log_level_suppresses_debug_at_info(monkeypatch, caplog):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("station", 0.8),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("train station", 0.6),
    )
    monkeypatch.setenv("CT_MIN_LOG_LEVEL", "INFO")

    with caplog.at_level("DEBUG", logger="consensus_translation.workflows"):
        run_local_job(
            text="车站",
            source_lang="zh",
            target_lang="ja",
            topic="travel",
        )

    debug_messages = [
        record.getMessage() for record in caplog.records if record.levelname == "DEBUG"
    ]
    info_messages = [
        record.getMessage() for record in caplog.records if record.levelname == "INFO"
    ]
    assert all("engine outputs captured" not in message for message in debug_messages)
    assert any("local workflow started" in message for message in info_messages)


def test_local_job_runtime_log_level_emits_debug_at_debug(monkeypatch, caplog):
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineA.translate",
        lambda _self, _text, _source, _target: ("station", 0.8),
    )
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("train station", 0.6),
    )
    monkeypatch.setenv("CT_MIN_LOG_LEVEL", "DEBUG")

    with caplog.at_level("DEBUG", logger="consensus_translation.workflows"):
        run_local_job(
            text="车站",
            source_lang="zh",
            target_lang="ja",
            topic="travel",
        )

    debug_messages = [
        record.getMessage() for record in caplog.records if record.levelname == "DEBUG"
    ]
    assert any("engine outputs captured" in message for message in debug_messages)
