from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_exe_script_exists_and_uses_onefile_pyinstaller() -> None:
    script = ROOT / "scripts" / "build_exe.ps1"

    assert script.exists()

    content = script.read_text(encoding="utf-8")
    assert "pyinstaller" in content.lower()
    assert "--onefile" in content
    assert "src/ui/pyqt_app/main_window.py" in content


def test_smoke_test_script_exists_and_checks_dist_exe() -> None:
    script = ROOT / "scripts" / "smoke_test_exe.ps1"

    assert script.exists()

    content = script.read_text(encoding="utf-8")
    assert "dist" in content.lower()
    assert ".exe" in content.lower()
