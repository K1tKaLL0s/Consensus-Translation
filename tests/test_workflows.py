from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


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
    assert result["final_text"] == "A::你好"
    assert result["final_score"] == pytest.approx(0.4525)
    assert result["needs_review"] is True
