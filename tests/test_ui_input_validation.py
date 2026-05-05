from src.ui.web_app.streamlit_app import validate_submission


def test_translate_mode_rejects_text_longer_than_1000_chars() -> None:
    ok, message = validate_submission(mode="翻译", source="book", text="a" * 1001)

    assert ok is False
    assert "1000" in message
