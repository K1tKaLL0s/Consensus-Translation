import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import AppSettings


def test_translation_char_limit_is_1000() -> None:
    settings = AppSettings()
    assert settings.translation_char_limit == 1000


def test_training_char_limit_is_unlimited() -> None:
    settings = AppSettings()
    assert settings.training_char_limit is None


def test_weight_sum_is_one() -> None:
    settings = AppSettings()
    total = settings.alpha + settings.beta + settings.gamma
    assert total == 1.0
