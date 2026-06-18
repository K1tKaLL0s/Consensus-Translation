from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
import json
from pathlib import Path
import subprocess
from typing import Callable, Literal

from consensus_translation.agent_packaging import check_desktop_packaging_ready
from consensus_translation.agent_release import check_desktop_release_ready


DiagnosticStatus = str
DiagnosticMode = Literal["developer", "installed"]


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class DiagnosticCheck:
    check_id: str
    status: DiagnosticStatus
    summary: str
    details: list[str]
    actions: list[str]


@dataclass(frozen=True)
class DiagnosticReport:
    overall_status: DiagnosticStatus
    checks: list[DiagnosticCheck]
    counts: dict[str, int]


CommandRunner = Callable[[list[str]], CommandResult]
ImportChecker = Callable[[str], object | None]


def _run_command(command: list[str]) -> CommandResult:
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=8,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _overall_status(checks: list[DiagnosticCheck]) -> DiagnosticStatus:
    if any(check.status == "error" for check in checks):
        return "error"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "ok"


def _counts(checks: list[DiagnosticCheck]) -> dict[str, int]:
    values = {"ok": 0, "warning": 0, "error": 0}
    for check in checks:
        values[check.status] = values.get(check.status, 0) + 1
    return values


def _packaging_check(
    project_root: Path,
    import_checker: ImportChecker,
) -> DiagnosticCheck:
    result = check_desktop_packaging_ready(project_root, import_checker=import_checker)
    details = [
        f"entrypoint: {result.entrypoint_path}",
        f"spec: {result.spec_path}",
        f"build_script: {result.build_script_path}",
        f"requirements: {result.requirements_path}",
    ]
    if result.missing:
        details.insert(0, "missing: " + ", ".join(result.missing))
    return DiagnosticCheck(
        check_id="desktop_packaging",
        status="ok" if result.ok else "error",
        summary="desktop packaging files are ready"
        if result.ok
        else "desktop packaging files are incomplete",
        details=details,
        actions=result.actions,
    )


def _release_check(project_root: Path) -> DiagnosticCheck:
    result = check_desktop_release_ready(project_root)
    details = [
        f"app_dir: {result.app_dir}",
        f"exe: {result.exe_path}",
        f"release_dir: {result.release_dir}",
    ]
    if result.missing:
        details.insert(0, "missing: " + ", ".join(result.missing))
    return DiagnosticCheck(
        check_id="desktop_release",
        status="ok" if result.ok else "error",
        summary="desktop release executable is present"
        if result.ok
        else "desktop release executable is missing",
        details=details,
        actions=result.actions,
    )


def _installed_app_check(install_root: Path) -> DiagnosticCheck:
    candidates = [
        install_root / "ConsensusTranslationAgent" / "ConsensusTranslationAgent.exe",
        install_root / "ConsensusTranslationAgent.exe",
    ]
    executable = next((path for path in candidates if path.is_file()), None)
    details = [f"install_root: {install_root}"]
    details.extend(f"candidate: {path}" for path in candidates)
    if executable is not None:
        details.insert(1, f"exe: {executable}")
        return DiagnosticCheck(
            check_id="desktop_install",
            status="ok",
            summary="installed desktop executable is present",
            details=details,
            actions=[],
        )
    return DiagnosticCheck(
        check_id="desktop_install",
        status="error",
        summary="installed desktop executable is missing",
        details=details,
        actions=["Reinstall the application into the selected install directory."],
    )


def _ocr_check(
    command_runner: CommandRunner,
    tesseract_command: str,
    required_languages: tuple[str, ...] = (),
) -> DiagnosticCheck:
    try:
        result = command_runner([tesseract_command, "--version"])
    except FileNotFoundError as exc:
        result = CommandResult(127, "", str(exc))
    except OSError as exc:
        result = CommandResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        result = CommandResult(124, exc.stdout or "", exc.stderr or "timeout")

    output = (result.stdout or result.stderr).strip()
    details = [f"command: {tesseract_command}"]
    if output:
        details.append(output)
    if result.returncode != 0:
        return DiagnosticCheck(
            check_id="ocr_tesseract",
            status="warning",
            summary="optional OCR runtime is unavailable",
            details=details,
            actions=[
                "Install Tesseract OCR and ensure tesseract is on PATH, or provide an injected OCR function."
            ],
        )

    if required_languages:
        try:
            language_result = command_runner([tesseract_command, "--list-langs"])
        except FileNotFoundError as exc:
            language_result = CommandResult(127, "", str(exc))
        except OSError as exc:
            language_result = CommandResult(127, "", str(exc))
        except subprocess.TimeoutExpired as exc:
            language_result = CommandResult(
                124,
                exc.stdout or "",
                exc.stderr or "timeout",
            )
        language_output = (
            language_result.stdout or language_result.stderr
        ).strip()
        if language_output:
            details.append(language_output)
        if language_result.returncode != 0:
            return DiagnosticCheck(
                check_id="ocr_tesseract",
                status="warning",
                summary="OCR runtime languages could not be inspected",
                details=details,
                actions=["Repair the Tesseract language data directory."],
            )
        available = {
            line.strip()
            for line in language_output.splitlines()
            if line.strip()
            and not line.strip().lower().startswith("list of available languages")
        }
        missing = [
            language
            for language in required_languages
            if language not in available
        ]
        details.append("required_languages: " + ", ".join(required_languages))
        details.append("available_languages: " + ", ".join(sorted(available)))
        if missing:
            details.append("missing_languages: " + ", ".join(missing))
            return DiagnosticCheck(
                check_id="ocr_tesseract",
                status="warning",
                summary="optional OCR runtime is missing required languages",
                details=details,
                actions=[
                    "Install the missing traineddata files into the configured Tesseract tessdata directory."
                ],
            )

    return DiagnosticCheck(
        check_id="ocr_tesseract",
        status="ok",
        summary="optional OCR runtime is available",
        details=details,
        actions=[],
    )


def _comet_check(
    import_checker: ImportChecker,
    command_runner: CommandRunner,
    comet_command: str,
) -> DiagnosticCheck:
    if import_checker("comet") is not None:
        return DiagnosticCheck(
            check_id="comet_runtime",
            status="ok",
            summary="optional COMET evaluator runtime is importable",
            details=["runtime: current Python process"],
            actions=[],
        )
    try:
        result = command_runner([comet_command, "--help"])
    except FileNotFoundError as exc:
        result = CommandResult(127, "", str(exc))
    except OSError as exc:
        result = CommandResult(127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        result = CommandResult(124, exc.stdout or "", exc.stderr or "timeout")
    output = (result.stdout or result.stderr).strip()
    details = [f"command: {comet_command}"]
    if output:
        details.append(output[:500])
    if result.returncode == 0:
        return DiagnosticCheck(
            check_id="comet_runtime",
            status="ok",
            summary="optional COMET evaluator sidecar is available",
            details=details,
            actions=[],
        )
    return DiagnosticCheck(
        check_id="comet_runtime",
        status="warning",
        summary="optional COMET evaluator runtime is unavailable",
        details=details,
        actions=[
            "Install COMET in an external Python environment and configure comet-score."
        ],
    )


def _provider_config_check(
    store: object | None,
    credential_store: object | None,
) -> DiagnosticCheck:
    if store is None:
        return DiagnosticCheck(
            check_id="provider_configs",
            status="warning",
            summary="provider configuration store is not attached",
            details=[],
            actions=["Run the desktop app with AgentRunStore to persist provider settings."],
        )

    lister = getattr(store, "list_provider_configs", None)
    if lister is None:
        return DiagnosticCheck(
            check_id="provider_configs",
            status="error",
            summary="provider store cannot list provider configs",
            details=[],
            actions=["Use AgentRunStore or provide a compatible provider config store."],
        )

    configs = list(lister(enabled=True))
    if not configs:
        return DiagnosticCheck(
            check_id="provider_configs",
            status="warning",
            summary="no enabled remote provider is configured",
            details=[],
            actions=["Save at least one enabled OpenAI-compatible provider for remote model use."],
        )

    if credential_store is None:
        return DiagnosticCheck(
            check_id="provider_configs",
            status="warning",
            summary="enabled providers exist, but credentials were not checked",
            details=[f"provider: {config.provider_id}" for config in configs],
            actions=["Attach LocalCredentialStore before running remote provider smoke tests."],
        )

    missing_credentials: list[str] = []
    for config in configs:
        try:
            credential_store.get_secret(config.credential_id)
        except KeyError:
            missing_credentials.append(
                f"missing credential {config.credential_id} for provider {config.provider_id}"
            )

    if missing_credentials:
        return DiagnosticCheck(
            check_id="provider_configs",
            status="warning",
            summary="some enabled providers are missing credentials",
            details=missing_credentials,
            actions=["Save provider API keys in the desktop provider settings panel."],
        )

    return DiagnosticCheck(
        check_id="provider_configs",
        status="ok",
        summary="enabled provider configs have stored credentials",
        details=[f"provider: {config.provider_id}" for config in configs],
        actions=[],
    )


def _gui_smoke_check() -> DiagnosticCheck:
    return DiagnosticCheck(
        check_id="gui_smoke",
        status="warning",
        summary="manual desktop launch smoke test is still required",
        details=[
            "Automated tests validate the controller and packaged files; a real GUI launch must be checked on the target desktop."
        ],
        actions=[
            "Run .\\run_desktop_agent.ps1 or release\\...\\ConsensusTranslationAgent.exe and verify the window opens."
        ],
    )


def run_desktop_diagnostics(
    project_root: str | Path,
    store: object | None = None,
    credential_store: object | None = None,
    command_runner: CommandRunner = _run_command,
    import_checker: ImportChecker = find_spec,
    tesseract_command: str = "tesseract",
    comet_command: str = "comet-score",
    mode: DiagnosticMode = "developer",
    required_ocr_languages: tuple[str, ...] = (),
) -> DiagnosticReport:
    root = Path(project_root).resolve()
    if mode == "developer":
        checks = [
            _packaging_check(root, import_checker),
            _release_check(root),
        ]
    elif mode == "installed":
        checks = [_installed_app_check(root)]
    else:
        raise ValueError(f"unsupported diagnostics mode: {mode}")
    checks.extend([
        _ocr_check(
            command_runner,
            tesseract_command,
            required_ocr_languages,
        ),
        _comet_check(import_checker, command_runner, comet_command),
        _provider_config_check(store, credential_store),
        _gui_smoke_check(),
    ])
    counts = _counts(checks)
    return DiagnosticReport(
        overall_status=_overall_status(checks),
        checks=checks,
        counts=counts,
    )


def format_diagnostic_lines(report: DiagnosticReport) -> list[str]:
    lines = [
        (
            f"diagnostics: {report.overall_status} | "
            f"ok={report.counts.get('ok', 0)} | "
            f"warning={report.counts.get('warning', 0)} | "
            f"error={report.counts.get('error', 0)}"
        )
    ]
    for check in report.checks:
        lines.append(f"[{check.status}] {check.check_id}: {check.summary}")
        lines.extend(f"  detail: {detail}" for detail in check.details)
        lines.extend(f"  action: {action}" for action in check.actions)
    return lines


def diagnostic_report_payload(report: DiagnosticReport) -> dict[str, object]:
    return {
        "overall_status": report.overall_status,
        "counts": dict(report.counts),
        "checks": [
            {
                "check_id": check.check_id,
                "status": check.status,
                "summary": check.summary,
                "details": list(check.details),
                "actions": list(check.actions),
            }
            for check in report.checks
        ],
    }


def write_diagnostic_report(
    report: DiagnosticReport,
    report_path: str | Path,
) -> Path:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            diagnostic_report_payload(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path
