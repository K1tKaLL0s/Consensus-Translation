from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_optional_runtime_installer_is_e_drive_scoped_and_reproducible():
    script_path = ROOT / "install_optional_runtimes.ps1"

    assert script_path.exists()
    source = script_path.read_text(encoding="utf-8")
    assert "-RuntimeRoot" in source
    assert "-DownloadTesseract" in source
    assert "-DownloadComet" in source
    assert "-DownloadModel" in source
    assert "-OfflineCache" in source
    assert "-InstalledMode" in source
    assert "Assert-DevelopmentRuntimeRoot" in source
    assert "tesseract-ocr-w64-setup-5.5.0.20241111.exe" in source
    assert "tesseract-ocr/tessdata_fast" in source
    assert "jpn" in source
    assert "chi_sim" in source
    assert "chi_tra" in source
    assert "python=3.11" in source
    assert "unbabel-comet==2.2.7" in source
    assert ".partial" in source
    assert "Get-FileHash" in source
    assert "expected_sha256" in source
    assert "PIP_CACHE_DIR" in source
    assert "--resume-retries" in source
    assert "CONDA_NO_PLUGINS" in source
    assert "CONDA_NUMBER_CHANNEL_NOTICES" in source
    assert "CONDA_SOLVER" in source
    assert "CONDA_PKGS_DIRS" in source
    assert "CONDA_ENVS_PATH" in source
    assert "HF_HOME" in source
    assert "TORCH_HOME" in source
    assert "download-comet-model.py" in source
    assert "Write-CometWrapper" in source
    assert "comet-score.cmd" in source
    assert "-m comet.cli.score" in source
    assert "snapshot_download" in source
    assert "max_workers=1" in source
    assert "comet-models" in source
