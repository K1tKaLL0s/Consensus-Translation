from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_ps1_contains_required_params_and_startup_commands() -> None:
    script_path = ROOT / "run.ps1"

    assert script_path.exists()

    content = script_path.read_text(encoding="utf-8")

    assert "[switch]$Init" in content
    assert "[ValidateSet(\"web\", \"desktop\", \"all\")]" in content
    assert "[string]$Mode = \"all\"" in content
    assert "[switch]$SkipInstall" in content
    assert "[switch]$SkipDB" in content

    assert "python -m venv venv" in content
    assert "pip install -r requirements.txt" in content
    assert "python -m src.tools.bootstrap_mysql" in content
    assert "uvicorn src.api.main:app" in content
    assert "streamlit" in content
    assert "src.ui.pyqt_app.main_window" in content
