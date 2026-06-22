from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_packaging import check_desktop_packaging_ready
from consensus_translation import desktop_agent_app
from consensus_translation.desktop_qt import application


def test_qt_packaging_preflight_detects_required_project_files():
    result = check_desktop_packaging_ready(
        ROOT,
        import_checker=lambda name: object(),
        variant="qt",
    )

    assert result.ok is True
    assert result.entrypoint_path == (
        ROOT / "src" / "consensus_translation" / "desktop_qt" / "application.py"
    )
    assert result.spec_path == ROOT / "packaging" / "desktop_agent_qt.spec"
    assert result.build_script_path == ROOT / "build_desktop_qt.ps1"
    assert result.requirements_path == ROOT / "requirements-desktop.txt"
    assert result.missing == []


def test_qt_spec_packages_help_and_release_documents():
    spec = (ROOT / "packaging" / "desktop_agent_qt.spec").read_text(encoding="utf-8")

    assert "consensus_translation.desktop_qt.application" in spec
    assert "docs/help" in spec
    assert "docs/user_manual_zh.md" in spec
    assert "MODEL_LICENSES.md" in spec
    assert "console=False" in spec
    assert '"tkinter"' in spec
    assert '"streamlit"' in spec
    assert '"torch"' in spec
    assert '"transformers"' in spec


def test_qt_build_script_uses_qt_spec_and_c_then_e_python_search():
    script = (ROOT / "build_desktop_qt.ps1").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-desktop.txt").read_text(encoding="utf-8")

    assert "packaging\\desktop_agent_qt.spec" in script
    assert "consensus_translation.agent_packaging --variant qt" in script
    assert "C:\\Python" in script
    assert "E:\\Ana\\python.exe" in script
    assert script.index("C:\\Python") < script.index("E:\\Ana\\python.exe")
    assert ".runtime\\python-packages-qt" in script
    assert "PYINSTALLER_CONFIG_DIR" in script
    assert "Library\\bin" in script
    assert "PySide6" in requirements


def test_qt_application_delegates_headless_cli_to_legacy_entrypoint(monkeypatch):
    captured = {}

    def fake_headless_main(argv):
        captured["argv"] = argv
        return 7

    monkeypatch.setattr(application, "_run_headless_cli", fake_headless_main)

    result = application.main(["--diagnostics", "--report-json", "report.json"])

    assert result == 7
    assert captured["argv"] == ["--diagnostics", "--report-json", "report.json"]


def test_installed_diagnostics_without_data_dir_uses_install_root_data(tmp_path):
    install_root = tmp_path / "installed"
    install_root.mkdir()
    (install_root / "ConsensusTranslationAgent.exe").write_bytes(b"exe")
    report_path = tmp_path / "diagnostics.json"

    result = desktop_agent_app.main(
        [
            "--diagnostics",
            "--diagnostics-mode",
            "installed",
            "--install-root",
            str(install_root),
            "--report-json",
            str(report_path),
        ]
    )

    assert result == 0
    assert report_path.is_file()
    assert (install_root / "data" / "agent.sqlite3").is_file()
