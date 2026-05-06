from __future__ import annotations

import os
from typing import Any

import requests


class LocalEngineA:
    engine_name = "marian-opus-mt"

    def __init__(self) -> None:
        self._translator_cache: dict[str, Any] = {}

    def is_available(self) -> bool:
        try:
            self._load_translator("Helsinki-NLP/opus-mt-zh-en")
            return True
        except Exception:
            return False

    def _normalize_lang(self, code: str) -> str:
        normalized = code.lower()
        if normalized.startswith("zh"):
            return "zh"
        if normalized.startswith("ja"):
            return "ja"
        if normalized.startswith("en"):
            return "en"
        return normalized

    def _load_translator(self, model_name: str):
        if model_name not in self._translator_cache:
            from transformers import pipeline

            self._translator_cache[model_name] = pipeline("translation", model=model_name)
        return self._translator_cache[model_name]

    def _run_model(self, text: str, model_name: str) -> str:
        translator = self._load_translator(model_name)
        result = translator(text, max_length=512)
        if not result or "translation_text" not in result[0]:
            raise RuntimeError(f"Marian model {model_name} returned empty output")
        translated = result[0]["translation_text"]
        if not isinstance(translated, str) or not translated:
            raise RuntimeError(f"Marian model {model_name} returned invalid output")
        return translated

    def _translate_with_marian(self, text: str, source_lang: str, target_lang: str) -> str:
        source = self._normalize_lang(source_lang)
        target = self._normalize_lang(target_lang)
        if source == target:
            return text

        direct_model = f"Helsinki-NLP/opus-mt-{source}-{target}"
        try:
            return self._run_model(text, direct_model)
        except Exception:
            if source == "en" or target == "en":
                raise

        pivot_model = f"Helsinki-NLP/opus-mt-{source}-en"
        target_model = f"Helsinki-NLP/opus-mt-en-{target}"
        pivot_text = self._run_model(text, pivot_model)
        return self._run_model(pivot_text, target_model)

    def translate(self, text: str, source_lang: str, target_lang: str) -> tuple[str, float]:
        translated = self._translate_with_marian(text, source_lang, target_lang)
        return translated, 0.66


class LocalEngineB:
    engine_name = "meta-nllb-200"

    def __init__(self) -> None:
        self._translator = None

    def _load_translator(self):
        if self._translator is None:
            from transformers import pipeline

            self._translator = pipeline(
                "translation",
                model="facebook/nllb-200-distilled-600M",
            )
        return self._translator

    def _normalize_lang(self, code: str) -> str:
        normalized = code.lower()
        if normalized.startswith("zh"):
            return "zh"
        if normalized.startswith("ja"):
            return "ja"
        if normalized.startswith("en"):
            return "en"
        return normalized

    def _to_nllb_code(self, code: str) -> str:
        mapping = {
            "zh": "zho_Hans",
            "ja": "jpn_Jpan",
            "en": "eng_Latn",
        }
        if code not in mapping:
            raise RuntimeError(f"NLLB does not support language code: {code}")
        return mapping[code]

    def _translate_with_nllb(self, text: str, source_lang: str, target_lang: str) -> str:
        translator = self._load_translator()
        src_code = self._to_nllb_code(source_lang)
        tgt_code = self._to_nllb_code(target_lang)
        result = translator(text, src_lang=src_code, tgt_lang=tgt_code, max_length=512)
        if not result or "translation_text" not in result[0]:
            raise RuntimeError("NLLB returned empty output")
        translated = result[0]["translation_text"]
        if not isinstance(translated, str) or not translated:
            raise RuntimeError("NLLB returned invalid output")
        return translated

    def translate(self, text: str, source_lang: str, target_lang: str) -> tuple[str, float]:
        source = self._normalize_lang(source_lang)
        target = self._normalize_lang(target_lang)

        if source == target:
            return text, 1.0

        translated = self._translate_with_nllb(text, source, target)
        return translated, 0.7
