from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation import agent_diagnostics
from consensus_translation.agent_diagnostics import (
    CommandResult,
    diagnostic_report_payload,
    format_diagnostic_lines,
    run_desktop_diagnostics,
)
from consensus_translation.agent_provider_config import ProviderConfig


class FakeProviderStore:
    def __init__(self, configs):
        self._configs = configs

    def list_provider_configs(self, enabled=None):
        if enabled is None:
            return self._configs
        return [config for config in self._configs if config.enabled is enabled]


class FakeCredentialStore:
    def __init__(self, secrets):
        self._secrets = secrets

    def get_secret(self, credential_id):
        if credential_id not in self._secrets:
            raise KeyError(f"credential not found: {credential_id}")
        return self._secrets[credential_id]


def _ready_project_root(root: Path) -> Path:
    (root / "src" / "consensus_translation").mkdir(parents=True)
    (root / "src" / "consensus_translation" / "desktop_agent_app.py").write_text(
        "# desktop entrypoint",
        encoding="utf-8",
    )
    (root / "packaging").mkdir()
    (root / "packaging" / "desktop_agent.spec").write_text(
        "# spec",
        encoding="utf-8",
    )
    (root / "build_desktop_agent.ps1").write_text(
        "# build",
        encoding="utf-8",
    )
    (root / "requirements-desktop.txt").write_text(
        "PyInstaller",
        encoding="utf-8",
    )
    (root / "install_optional_runtimes.ps1").write_text(
        "# runtime installer",
        encoding="utf-8",
    )
    app_dir = root / "dist" / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"exe")
    (root / "README.md").write_text("# Readme", encoding="utf-8")
    return root


def _config(provider_id="remote-a", credential_id="remote-a-key", enabled=True):
    return ProviderConfig(
        provider_id=provider_id,
        kind="openai_compatible",
        base_url="https://api.example.test/v1",
        model="translator",
        credential_id=credential_id,
        estimated_cost=0.25,
        enabled=enabled,
    )


def test_desktop_diagnostics_reports_ready_runtime_with_manual_gui_warning(tmp_path):
    root = _ready_project_root(tmp_path)
    store = FakeProviderStore([_config()])
    credentials = FakeCredentialStore({"remote-a-key": "sk-test"})

    report = run_desktop_diagnostics(
        root,
        store=store,
        credential_store=credentials,
        command_runner=lambda command: CommandResult(0, "tesseract 5.0", ""),
        import_checker=lambda name: object(),
    )

    statuses = {check.check_id: check.status for check in report.checks}
    assert statuses["desktop_packaging"] == "ok"
    assert statuses["desktop_release"] == "ok"
    assert statuses["ocr_tesseract"] == "ok"
    assert statuses["comet_runtime"] == "ok"
    assert statuses["provider_configs"] == "ok"
    assert statuses["gui_smoke"] == "warning"
    assert report.overall_status == "warning"
    assert report.counts["ok"] == 5
    assert report.counts["warning"] == 1
    assert report.counts["error"] == 0


def test_command_runner_allows_slow_optional_sidecars(monkeypatch):
    captured = {}

    def fake_run(command, capture_output, check, text, timeout):
        captured["command"] = command
        captured["timeout"] = timeout

        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Result()

    monkeypatch.setattr(agent_diagnostics.subprocess, "run", fake_run)

    result = agent_diagnostics._run_command(["comet-score", "--help"])

    assert result.returncode == 0
    assert captured["command"] == ["comet-score", "--help"]
    assert captured["timeout"] >= 60


def test_installed_diagnostics_does_not_require_build_tooling(tmp_path):
    install_root = tmp_path / "installed"
    app_dir = install_root / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"exe")

    report = run_desktop_diagnostics(
        install_root,
        mode="installed",
        command_runner=lambda command: CommandResult(0, "ok", ""),
        import_checker=lambda name: None,
    )

    checks = {item.check_id: item for item in report.checks}
    assert "desktop_packaging" not in checks
    assert "desktop_release" not in checks
    assert checks["desktop_install"].status == "ok"
    assert report.counts["error"] == 0


def test_ocr_diagnostics_checks_required_languages(tmp_path):
    install_root = tmp_path / "installed"
    app_dir = install_root / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"exe")

    def runner(command):
        if command[-1] == "--version":
            return CommandResult(0, "tesseract 5.5", "")
        if command[-1] == "--list-langs":
            return CommandResult(
                0,
                'List of available languages in "tessdata" (2):\neng\nosd',
                "",
            )
        return CommandResult(127, "", "not found")

    report = run_desktop_diagnostics(
        install_root,
        mode="installed",
        command_runner=runner,
        import_checker=lambda name: None,
        required_ocr_languages=("eng", "jpn"),
    )

    check = next(item for item in report.checks if item.check_id == "ocr_tesseract")
    assert check.status == "warning"
    assert "jpn" in " ".join(check.details)


def test_desktop_diagnostics_flags_optional_runtime_and_provider_gaps(tmp_path):
    root = _ready_project_root(tmp_path)
    store = FakeProviderStore([_config()])
    credentials = FakeCredentialStore({})

    report = run_desktop_diagnostics(
        root,
        store=store,
        credential_store=credentials,
        command_runner=lambda command: CommandResult(127, "", "not found"),
        import_checker=lambda name: object() if name == "PyInstaller" else None,
    )

    checks = {check.check_id: check for check in report.checks}
    assert checks["ocr_tesseract"].status == "warning"
    assert checks["comet_runtime"].status == "warning"
    assert checks["provider_configs"].status == "warning"
    assert "remote-a-key" in checks["provider_configs"].details[0]
    assert any("Tesseract" in action for action in checks["ocr_tesseract"].actions)
    assert report.overall_status == "warning"


def test_desktop_diagnostics_treats_missing_packaging_and_release_as_errors(tmp_path):
    report = run_desktop_diagnostics(
        tmp_path,
        store=None,
        credential_store=None,
        command_runner=lambda command: CommandResult(127, "", "not found"),
        import_checker=lambda name: None,
    )

    statuses = {check.check_id: check.status for check in report.checks}
    assert statuses["desktop_packaging"] == "error"
    assert statuses["desktop_release"] == "error"
    assert statuses["provider_configs"] == "warning"
    assert report.overall_status == "error"
    assert report.counts["error"] == 2


def test_format_diagnostic_lines_summarizes_statuses(tmp_path):
    root = _ready_project_root(tmp_path)
    report = run_desktop_diagnostics(
        root,
        store=FakeProviderStore([]),
        credential_store=FakeCredentialStore({}),
        command_runner=lambda command: CommandResult(0, "tesseract 5.0", ""),
        import_checker=lambda name: object(),
    )

    lines = format_diagnostic_lines(report)

    assert lines[0].startswith("diagnostics: warning")
    assert any("[ok] desktop_packaging:" in line for line in lines)
    assert any("[warning] provider_configs:" in line for line in lines)
    assert any("action:" in line for line in lines)


def test_diagnostic_report_payload_is_machine_readable(tmp_path):
    root = _ready_project_root(tmp_path)
    report = run_desktop_diagnostics(
        root,
        store=FakeProviderStore([]),
        credential_store=FakeCredentialStore({}),
        command_runner=lambda command: CommandResult(0, "runtime ok", ""),
        import_checker=lambda name: object(),
    )

    payload = diagnostic_report_payload(report)

    assert payload["overall_status"] == "warning"
    assert payload["counts"]["error"] == 0
    assert payload["checks"][0]["check_id"] == "desktop_packaging"
    assert all("status" in check for check in payload["checks"])
