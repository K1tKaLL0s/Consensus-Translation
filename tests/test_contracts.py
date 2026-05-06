from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.config import AppSettings


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
