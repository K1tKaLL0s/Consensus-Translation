from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from consensus_translation.runtime_manifest import RuntimeManifest


def test_runtime_manifest_requires_all_ocr_languages():
    manifest = RuntimeManifest.default()

    assert manifest.ocr_languages == ("eng", "jpn", "chi_sim", "chi_tra")
    assert manifest.comet_model == "Unbabel/wmt22-comet-da"
    assert all(download.sha256 for download in manifest.downloads)
    assert all(download.expected_size > 0 for download in manifest.downloads)


def test_runtime_manifest_rejects_non_e_development_root():
    with pytest.raises(ValueError, match="E drive"):
        RuntimeManifest.default().validate_development_root(Path("C:/runtime"))


def test_runtime_manifest_allows_installed_root_on_user_selected_drive():
    manifest = RuntimeManifest.default()

    assert manifest.validate_installed_root(Path("C:/Users/example/App")) == Path(
        "C:/Users/example/App"
    ).resolve()


def test_runtime_manifest_writes_relative_settings_for_installed_runtime(tmp_path):
    install_root = tmp_path / "install"
    runtime_root = install_root / "runtime"

    settings = RuntimeManifest.default().runtime_settings(
        runtime_root=runtime_root,
        install_root=install_root,
    )

    assert settings["runtime_root"] == "runtime"
    assert settings["tesseract_command"] == "runtime/Tesseract-OCR/tesseract.exe"
    assert settings["comet_model_storage_path"] == "runtime/comet-models"
