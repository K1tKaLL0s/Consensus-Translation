from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_packaging import check_desktop_packaging_ready


def test_desktop_packaging_preflight_detects_required_project_files():
    result = check_desktop_packaging_ready(ROOT, import_checker=lambda name: object())

    assert result.ok is True
    assert result.entrypoint_path == ROOT / "src" / "consensus_translation" / "desktop_agent_app.py"
    assert result.spec_path == ROOT / "packaging" / "desktop_agent.spec"
    assert result.build_script_path == ROOT / "build_desktop_agent.ps1"
    assert result.requirements_path == ROOT / "requirements-desktop.txt"
    assert result.missing == []


def test_desktop_packaging_preflight_reports_missing_pyinstaller():
    result = check_desktop_packaging_ready(ROOT, import_checker=lambda name: None)

    assert result.ok is False
    assert "pyinstaller" in result.missing
    assert any("python -m pip install -r requirements-desktop.txt" in item for item in result.actions)


def test_desktop_packaging_files_define_tkinter_agent_entrypoint():
    spec = (ROOT / "packaging" / "desktop_agent.spec").read_text(encoding="utf-8")
    script = (ROOT / "build_desktop_agent.ps1").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements-desktop.txt").read_text(encoding="utf-8")

    assert "desktop_agent_app.py" in spec
    assert "ConsensusTranslationAgent" in spec
    assert "console=False" in spec
    assert "PyInstaller" in requirements
    assert "packaging\\desktop_agent.spec" in script
    assert "consensus_translation.agent_acceptance" in spec
    assert "consensus_translation.agent_packaging" in script
    assert "consensus_translation.agent_input_plugins" in spec
    assert "consensus_translation.agent_diagnostics" in spec
    assert "consensus_translation.agent_runtime" in spec


def test_desktop_packaging_spec_resolves_project_root_from_packaging_or_root_path():
    spec = (ROOT / "packaging" / "desktop_agent.spec").read_text(encoding="utf-8")

    assert "if not (project_root / \"src\").exists()" in spec
    assert "project_root = project_root.parent" in spec


def test_desktop_packaging_spec_excludes_heavy_non_desktop_packages():
    spec = (ROOT / "packaging" / "desktop_agent.spec").read_text(encoding="utf-8")

    for package_name in [
        "IPython",
        "matplotlib",
        "numpy",
        "torch",
        "transformers",
    ]:
        assert f'"{package_name}"' in spec
