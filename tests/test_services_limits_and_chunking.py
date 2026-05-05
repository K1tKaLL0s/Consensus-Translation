from src.services.training_service import chunk_training_text
from src.services.translation_service import validate_source_declaration, validate_translation_input


def test_translation_rejects_text_longer_than_configured_limit(monkeypatch) -> None:
    class FakeSettings:
        translation_char_limit = 5

    monkeypatch.setattr("src.services.translation_service.AppSettings", FakeSettings)

    ok, message = validate_translation_input("a" * 6)

    assert ok is False
    assert message != "ok"


def test_translation_accepts_text_within_configured_limit(monkeypatch) -> None:
    class FakeSettings:
        translation_char_limit = 8

    monkeypatch.setattr("src.services.translation_service.AppSettings", FakeSettings)

    ok, message = validate_translation_input("a" * 8)

    assert ok is True
    assert message == "ok"


def test_source_declaration_rejects_blank_source() -> None:
    ok, message = validate_source_declaration("   ")

    assert ok is False
    assert message != "ok"


def test_source_declaration_accepts_non_empty_source() -> None:
    ok, message = validate_source_declaration("from glossary.md")

    assert ok is True
    assert message == "ok"


def test_training_chunks_25000_chars_into_five_chunks_of_5000() -> None:
    chunks = chunk_training_text("b" * 25000, chunk_size=5000)

    assert len(chunks) == 5
    assert all(len(chunk) == 5000 for chunk in chunks)


def test_training_chunk_size_must_be_positive() -> None:
    try:
        chunk_training_text("abc", chunk_size=0)
        assert False, "Expected ValueError for chunk_size <= 0"
    except ValueError:
        pass
