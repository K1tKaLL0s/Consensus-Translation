import pytest

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
    assert total == pytest.approx(1.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"alpha": -0.1},
        {"beta": 1.1},
        {"gamma": -0.01},
        {"alpha": 0.6, "beta": 0.3, "gamma": 0.05},
        {"confidence_threshold": 1.1},
        {"translation_char_limit": 0},
    ],
)
def test_invalid_settings_raise_value_error(kwargs: dict[str, float | int]) -> None:
    with pytest.raises(ValueError):
        AppSettings(**kwargs)
