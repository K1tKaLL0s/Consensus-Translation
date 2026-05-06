from pathlib import Path
import sys
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.config import AppSettings
from pydantic import ValidationError

from consensus_translation.contracts import (
    StageStatus,
    TranslationJobContract,
)


def test_default_settings_use_v1_contract_and_three_level_granularity():
    settings = AppSettings()

    assert settings.contract_version == "1.0.0"
    assert settings.default_granularity == ["token", "sentence", "segment"]
    assert settings.mdwc_weights == {
        "token": 0.4,
        "sentence": 0.35,
        "segment": 0.2,
        "user_prior": 0.05,
    }


def test_contract_stage_sequence_starts_with_ingest_and_ends_with_finalize():
    statuses = list(StageStatus)

    assert statuses[0] == StageStatus.INGEST
    assert statuses[-1] == StageStatus.FINALIZE


def test_contract_requires_version_match():
    with pytest.raises(ValidationError):
        TranslationJobContract(
            contract_version="2.0.0",
            job_id="job-123",
            mode="standard",
            source_lang="zh",
            target_lang="ja",
            topic="general",
        )
