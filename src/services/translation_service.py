def validate_translation_input(text: str) -> tuple[bool, str]:
    if len(text) > 1000:
        return False, "text length must be <= 1000"
    return True, "ok"
