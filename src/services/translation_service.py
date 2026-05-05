from src.core.config import AppSettings


def validate_source_declaration(source: str) -> tuple[bool, str]:
    if not source.strip():
        return False, "source declaration must not be blank"
    return True, "ok"


def validate_translation_input(text: str) -> tuple[bool, str]:
    limit = AppSettings().translation_char_limit
    if len(text) > limit:
        return False, f"text length must be <= {limit}"
    return True, "ok"
