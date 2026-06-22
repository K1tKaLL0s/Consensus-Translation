from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.engines import (
    LocalEngineA,
    LocalEngineB,
    ResearchNllbEngine,
)


def test_local_engine_a_and_b_expose_expected_ids():
    assert LocalEngineA().engine_name == "marian-opus-mt"
    assert LocalEngineB().engine_name == "marian-opus-pivot"


def test_engine_translate_signature_accepts_language_pair(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.engines.LocalEngineA._translate_with_marian",
        lambda _self, text, source_lang, target_lang: "hello",
    )

    text, confidence = LocalEngineA().translate("你好", "zh", "en")

    assert text == "hello"
    assert 0.0 <= confidence <= 1.0


def test_commercial_engine_b_uses_english_pivot(monkeypatch):
    calls = []

    def _fake_run(self, text, model_name):
        calls.append((text, model_name))
        return "english" if model_name.endswith("ja-en") else "中文"

    monkeypatch.setattr(
        "consensus_translation.engines.LocalEngineB._run_model",
        _fake_run,
    )

    translated, confidence = LocalEngineB().translate("こんにちは", "ja", "zh")

    assert translated == "中文"
    assert confidence == 0.62
    assert calls == [
        ("こんにちは", "Helsinki-NLP/opus-mt-ja-en"),
        ("english", "Helsinki-NLP/opus-mt-en-zh"),
    ]


def test_nllb_engine_uses_language_mapping(monkeypatch):
    calls = {}

    def _fake_load(self):
        def _translator(text, src_lang, tgt_lang, max_length):
            calls["text"] = text
            calls["src_lang"] = src_lang
            calls["tgt_lang"] = tgt_lang
            calls["max_length"] = max_length
            return [{"translation_text": "hello"}]

        return _translator

    monkeypatch.setattr(
        "consensus_translation.engines.ResearchNllbEngine._load_translator",
        _fake_load,
    )

    translated, confidence = ResearchNllbEngine().translate("你好", "zh", "en")

    assert translated == "hello"
    assert confidence == 0.7
    assert calls["text"] == "你好"
    assert calls["src_lang"] == "zho_Hans"
    assert calls["tgt_lang"] == "eng_Latn"
