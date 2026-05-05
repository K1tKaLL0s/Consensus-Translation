from src.services.translation_service import validate_translation_input


def test_translate_mode_rejects_text_longer_than_1000_chars() -> None:
    ok, message = validate_translation_input("a" * 1001)

    assert ok is False
    assert "1000" in message
