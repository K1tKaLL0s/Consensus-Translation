from pathlib import Path
import json
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_release import (
    DesktopReleaseBuild,
    build_desktop_release_package,
    check_desktop_release_ready,
)


def _create_dist_tree(root: Path) -> None:
    app_dir = root / "dist" / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"desktop exe")
    (app_dir / "support.dat").write_text("support file", encoding="utf-8")
    (root / "README.md").write_text("# Readme", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir()
    (docs / "user_manual_zh.md").write_text("# Manual", encoding="utf-8")
    (docs / "desktop_agent_core_zh.md").write_text("# Core", encoding="utf-8")
    (root / "install_optional_runtimes.ps1").write_text(
        "# runtime installer",
        encoding="utf-8",
    )


def test_check_desktop_release_ready_reports_missing_dist(tmp_path):
    result = check_desktop_release_ready(tmp_path)

    assert result.ok is False
    assert result.app_dir == tmp_path / "dist" / "ConsensusTranslationAgent"
    assert result.exe_path == result.app_dir / "ConsensusTranslationAgent.exe"
    assert result.missing == [
        "desktop-dist",
        "desktop-exe",
        "readme",
        "runtime-installer",
    ]
    assert any("build_desktop_agent.ps1" in action for action in result.actions)


def test_build_desktop_release_package_writes_manifest_and_zip(tmp_path):
    _create_dist_tree(tmp_path)

    result = build_desktop_release_package(
        tmp_path,
        version="1.2.3",
        channel="portable",
    )

    assert isinstance(result, DesktopReleaseBuild)
    assert result.version == "1.2.3"
    assert result.channel == "portable"
    assert result.zip_path.exists()
    assert result.manifest_path.exists()
    assert result.exe_sha256
    assert result.zip_sha256

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["app_name"] == "ConsensusTranslationAgent"
    assert manifest["version"] == "1.2.3"
    assert manifest["channel"] == "portable"
    assert manifest["entrypoint"] == "ConsensusTranslationAgent.exe"
    assert manifest["artifacts"]["exe"]["sha256"] == result.exe_sha256
    assert manifest["artifacts"]["zip"]["sha256"] == result.zip_sha256
    assert manifest["included_docs"] == [
        "README.md",
        "docs/user_manual_zh.md",
        "docs/desktop_agent_core_zh.md",
    ]
    assert manifest["included_scripts"] == ["install_optional_runtimes.ps1"]
    assert manifest["external_requirements"]["ocr"] == "optional-tesseract-cli"
    assert manifest["external_requirements"]["remote_api"] == "optional-openai-compatible-provider"
    assert manifest["license_profile"] == "portable-dev"
    assert manifest["not_included"] == [
        "code-signing",
        "installer",
        "auto-update",
        "live-remote-provider-validation",
    ]

    with zipfile.ZipFile(result.zip_path) as archive:
        names = sorted(archive.namelist())
        inner_manifest = json.loads(
            archive.read("release-manifest.json").decode("utf-8")
        )

    assert "ConsensusTranslationAgent/ConsensusTranslationAgent.exe" in names
    assert "ConsensusTranslationAgent/support.dat" in names
    assert "README.md" in names
    assert "docs/user_manual_zh.md" in names
    assert "install_optional_runtimes.ps1" in names
    assert "release-manifest.json" in names
    assert inner_manifest["artifacts"]["zip"]["sha256"] == ""
    assert inner_manifest["artifacts"]["zip"]["bytes"] == 0
    assert inner_manifest["artifacts"]["zip"]["hash_source"] == "sidecar-manifest"


def test_desktop_release_script_exists_and_invokes_release_module():
    script = (ROOT / "build_desktop_release.ps1").read_text(encoding="utf-8")
    acceptance_script = (ROOT / "run_desktop_acceptance.ps1").read_text(
        encoding="utf-8"
    )

    assert "consensus_translation.agent_release" in script
    assert "build_desktop_qt.ps1" in script
    assert acceptance_script.lstrip().startswith("param(")
    assert "consensus_translation.agent_acceptance" in acceptance_script
    assert "--report-json" in acceptance_script


def test_release_manifest_records_installer_and_license_profile(tmp_path):
    _create_dist_tree(tmp_path)
    installer = tmp_path / "ConsensusTranslationAgent-Setup.exe"
    installer.write_bytes(b"setup")

    result = build_desktop_release_package(
        tmp_path,
        version="2026.06.18",
        channel="full",
        license_profile="commercial-safe",
        installer_path=installer,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["license_profile"] == "commercial-safe"
    assert manifest["artifacts"]["installer"]["path"] == installer.name
    assert manifest["artifacts"]["installer"]["sha256"]
    assert manifest["artifacts"]["installer"]["bytes"] == installer.stat().st_size
    assert "code-signing" in manifest["not_included"]
    assert "installer" not in manifest["not_included"]
    assert manifest["runtime_verification"]["status"] == "not-run"


def test_installed_release_verifier_script_contract():
    script = (ROOT / "scripts" / "verify_installed_release.ps1").read_text(
        encoding="utf-8"
    )

    assert "-InstallerPath" in script
    assert "-InstallDir" in script
    assert "/VERYSILENT" in script
    assert "/DIR=" in script
    assert "/TASKS=desktopicon" in script
    assert "--diagnostics-mode" in script
    assert "--local-smoke" in script
    assert "GetFolderPath('Desktop')" in script
    assert "UninstallString" in script
