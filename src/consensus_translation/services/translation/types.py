from __future__ import annotations

SUPPORTED_TRANSLATION_LANGUAGES: tuple[str, ...] = (
    "auto",
    "zh",
    "en",
    "ja",
    "ko",
    "fr",
    "de",
    "es",
)

TARGET_TRANSLATION_LANGUAGES: tuple[str, ...] = tuple(
    language for language in SUPPORTED_TRANSLATION_LANGUAGES if language != "auto"
)

ENGLISH_LANGUAGE_NAMES: dict[str, str] = {
    "auto": "Auto Detect",
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
}
