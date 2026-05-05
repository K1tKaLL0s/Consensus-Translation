from src.services.translation_service import validate_translation_input
from src.ui.web_app.streamlit_app import validate_submission


def test_translate_mode_rejects_text_longer_than_1000_chars() -> None:
    ok, message = validate_translation_input("a" * 1001)

    assert ok is False
    assert "1000" in message


def test_validate_submission_rejects_blank_source() -> None:
    ok, message = validate_submission(mode="翻译", source="   ", text="abc")

    assert ok is False
    assert message == "source declaration must not be blank"


def test_validate_submission_rejects_translate_text_over_limit() -> None:
    class _Settings:
        translation_char_limit = 10

    from src.services import translation_service

    original_settings = translation_service.AppSettings
    translation_service.AppSettings = _Settings

    try:
        ok, message = validate_submission(mode="翻译", source="新闻", text="a" * 11)
    finally:
        translation_service.AppSettings = original_settings

    assert ok is False
    assert "10" in message


def test_validate_submission_allows_training_text_over_limit() -> None:
    ok, message = validate_submission(mode="训练", source="新闻", text="a" * 1001)

    assert ok is True
    assert message == "提交成功"
