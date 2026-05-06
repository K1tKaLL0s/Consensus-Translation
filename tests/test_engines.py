from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.engines import LocalEngineA, LocalEngineB


def test_local_engine_a_and_b_expose_expected_ids():
    assert LocalEngineA().engine_name == "marian-opus-mt"
    assert LocalEngineB().engine_name == "meta-nllb-200"


def test_engine_translate_signature_accepts_language_pair(monkeypatch):
    monkeypatch.setattr(
        "consensus_translation.engines.LocalEngineA._translate_with_marian",
        lambda _self, text, source_lang, target_lang: "hello",
    )

    text, confidence = LocalEngineA().translate("你好", "zh", "en")

    assert text == "hello"
    assert 0.0 <= confidence <= 1.0


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

    monkeypatch.setattr("consensus_translation.engines.LocalEngineB._load_translator", _fake_load)

    translated, confidence = LocalEngineB().translate("你好", "zh", "en")

    assert translated == "hello"
    assert confidence == 0.7
    assert calls["text"] == "你好"
    assert calls["src_lang"] == "zho_Hans"
    assert calls["tgt_lang"] == "eng_Latn"
