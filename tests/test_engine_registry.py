from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.engine_registry import EngineRegistry


def test_commercial_safe_profile_excludes_nllb():
    registry = EngineRegistry.default()

    ids = [entry.engine_id for entry in registry.enabled_for("commercial-safe")]

    assert "marian-opus-direct" in ids
    assert "marian-opus-pivot" in ids
    assert "nllb-200-distilled-600m" not in ids


def test_research_profile_marks_nllb_as_user_download():
    entry = EngineRegistry.default().get("nllb-200-distilled-600m")

    assert entry.license_id == "CC-BY-NC-4.0"
    assert entry.commercial_use is False
    assert entry.bundled is False
    assert entry.requires_license_acceptance is True


def test_registry_records_exact_commercial_opus_models():
    registry = EngineRegistry.default()
    model_ids = {
        model_id
        for entry in registry.enabled_for("commercial-safe")
        for model_id in entry.model_ids
    }

    assert model_ids == {
        "Helsinki-NLP/opus-mt-zh-en",
        "Helsinki-NLP/opus-mt-en-zh",
        "Helsinki-NLP/opus-mt-ja-en",
        "Helsinki-NLP/opus-mt-en-jap",
        "Helsinki-NLP/opus-mt-tc-big-zh-ja",
    }
