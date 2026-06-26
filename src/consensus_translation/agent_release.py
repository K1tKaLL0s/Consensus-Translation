from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from collections.abc import Sequence


@dataclass(frozen=True)
class DesktopReleasePreflight:
    ok: bool
    app_dir: Path
    exe_path: Path
    release_dir: Path
    missing: list[str]
    actions: list[str]


@dataclass(frozen=True)
class DesktopReleaseBuild:
    version: str
    channel: str
    release_dir: Path
    manifest_path: Path
    zip_path: Path
    exe_sha256: str
    zip_sha256: str
    installer_sha256: str | None = None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mock_provider_guard_ready(root: Path) -> bool:
    required_markers = {
        root / "src" / "consensus_translation" / "desktop_agent_app.py": (
            "allow_mock_providers: bool = False",
            "mock providers are disabled for production desktop runs",
        ),
        root / "src" / "consensus_translation" / "agent_workflows.py": (
            "allow_mock_providers: bool = False",
            "mock providers are disabled for production workflow runs",
            "finalize_guard:decision_requires_human_review",
        ),
    }
    for path, markers in required_markers.items():
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            return False
        if any(marker not in source for marker in markers):
            return False
    return True


def _file_artifact(path: Path, root: Path | None = None) -> dict[str, object]:
    artifact_path = Path(path).resolve()
    if root is not None:
        try:
            display_path = str(artifact_path.relative_to(root)).replace("\\", "/")
        except ValueError:
            display_path = artifact_path.name
    else:
        display_path = artifact_path.name
    return {
        "path": display_path,
        "sha256": _sha256_file(artifact_path),
        "bytes": artifact_path.stat().st_size,
    }


def check_desktop_release_ready(project_root: str | Path) -> DesktopReleasePreflight:
    root = Path(project_root).resolve()
    app_dir = root / "dist" / "ConsensusTranslationAgent"
    exe_path = app_dir / "ConsensusTranslationAgent.exe"
    release_dir = root / "release"

    missing: list[str] = []
    if not app_dir.exists():
        missing.append("desktop-dist")
    if not exe_path.exists():
        missing.append("desktop-exe")
    if not (root / "README.md").exists():
        missing.append("readme")
    if not (root / "install_optional_runtimes.ps1").exists():
        missing.append("runtime-installer")
    if not _mock_provider_guard_ready(root):
        missing.append("mock-provider-guard")

    actions: list[str] = []
    if "desktop-dist" in missing or "desktop-exe" in missing:
        actions.append("powershell -ExecutionPolicy Bypass -File .\\build_desktop_agent.ps1")
    if "readme" in missing:
        actions.append("restore README.md")
    if "runtime-installer" in missing:
        actions.append("restore install_optional_runtimes.ps1")
    if "mock-provider-guard" in missing:
        actions.append("restore production mock-provider and finalize guards before release")

    return DesktopReleasePreflight(
        ok=not missing,
        app_dir=app_dir,
        exe_path=exe_path,
        release_dir=release_dir,
        missing=missing,
        actions=actions,
    )


def _doc_paths(root: Path) -> list[Path]:
    candidates = [
        root / "README.md",
        root / "docs" / "user_manual_zh.md",
        root / "docs" / "desktop_agent_core_zh.md",
    ]
    return [path for path in candidates if path.exists()]


def _script_paths(root: Path) -> list[Path]:
    candidates = [root / "install_optional_runtimes.ps1"]
    return [path for path in candidates if path.exists()]


def _runtime_verification_payload(root: Path) -> dict[str, object]:
    report_path = root / ".runtime" / "runtime-verification.json"
    if not report_path.is_file():
        return {"status": "not-run"}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "invalid-report",
            "report_path": str(report_path.relative_to(root)).replace("\\", "/"),
        }
    ok = bool(payload.get("ok"))
    return {
        "status": "ok" if ok else "failed",
        "report_path": str(report_path.relative_to(root)).replace("\\", "/"),
        "tesseract_version": payload.get("tesseract_version", ""),
        "ocr_languages": payload.get("ocr_languages", []),
        "comet_cli_ok": bool(payload.get("comet_cli_ok")),
        "comet_model_ok": bool(payload.get("comet_model_ok")),
        "comet_score": payload.get("comet_score"),
    }


def _installer_artifact_payload(installer_path: Path, root: Path) -> dict[str, object]:
    installer = Path(installer_path).resolve()
    payload = _file_artifact(installer, root)
    slice_paths = sorted(installer.parent.glob(f"{installer.stem}-*.bin"))
    payload["slices"] = [_file_artifact(path, root) for path in slice_paths]
    return payload


def _installer_paths(value: str | Path | Sequence[str | Path] | None) -> list[Path]:
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        return [Path(value)]
    return [Path(path) for path in value]


def _write_zip(
    app_dir: Path,
    docs: list[Path],
    scripts: list[Path],
    manifest_path: Path,
    zip_path: Path,
    root: Path,
) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(app_dir.rglob("*")):
            if path.is_file():
                archive.write(
                    path,
                    Path("ConsensusTranslationAgent") / path.relative_to(app_dir),
                )
        for doc in docs:
            archive.write(doc, doc.relative_to(root))
        for script in scripts:
            archive.write(script, script.relative_to(root))
        archive.write(manifest_path, "release-manifest.json")


def build_desktop_release_package(
    project_root: str | Path,
    version: str,
    channel: str = "portable",
    license_profile: str = "portable-dev",
    installer_path: str | Path | Sequence[str | Path] | None = None,
) -> DesktopReleaseBuild:
    root = Path(project_root).resolve()
    preflight = check_desktop_release_ready(root)
    if not preflight.ok:
        missing = ", ".join(preflight.missing)
        raise FileNotFoundError(f"desktop release preflight failed: {missing}")

    release_name = f"ConsensusTranslationAgent-{version}-{channel}"
    release_dir = preflight.release_dir / release_name
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True)

    docs = _doc_paths(root)
    scripts = _script_paths(root)
    exe_sha256 = _sha256_file(preflight.exe_path)
    zip_path = preflight.release_dir / f"{release_name}.zip"
    manifest_path = release_dir / "release-manifest.json"

    installer_artifacts = [
        _installer_artifact_payload(path, root)
        for path in _installer_paths(installer_path)
    ]
    primary_installer = (
        installer_artifacts[0]
        if installer_artifacts
        else None
    )
    not_included = [
        "code-signing",
        "auto-update",
        "live-remote-provider-validation",
    ]
    if primary_installer is None:
        not_included.insert(1, "installer")

    manifest = {
        "app_name": "ConsensusTranslationAgent",
        "version": version,
        "channel": channel,
        "license_profile": license_profile,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "entrypoint": "ConsensusTranslationAgent.exe",
        "artifacts": {
            "exe": {
                "path": "ConsensusTranslationAgent/ConsensusTranslationAgent.exe",
                "sha256": exe_sha256,
                "bytes": preflight.exe_path.stat().st_size,
            },
            "zip": {
                "path": zip_path.name,
                "sha256": "",
                "bytes": 0,
                "hash_source": "sidecar-manifest",
            },
        },
        "included_docs": [str(path.relative_to(root)).replace("\\", "/") for path in docs],
        "included_scripts": [
            str(path.relative_to(root)).replace("\\", "/") for path in scripts
        ],
        "external_requirements": {
            "ocr": "optional-tesseract-cli",
            "remote_api": "optional-openai-compatible-provider",
            "comet": "optional-comet-runtime",
        },
        "runtime_verification": _runtime_verification_payload(root),
        "not_included": not_included,
    }
    if primary_installer is not None:
        manifest["artifacts"]["installer"] = primary_installer
        manifest["artifacts"]["installers"] = installer_artifacts
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if zip_path.exists():
        zip_path.unlink()
    _write_zip(preflight.app_dir, docs, scripts, manifest_path, zip_path, root)
    final_zip_sha256 = _sha256_file(zip_path)
    manifest["artifacts"]["zip"]["sha256"] = final_zip_sha256
    manifest["artifacts"]["zip"]["bytes"] = zip_path.stat().st_size
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return DesktopReleaseBuild(
        version=version,
        channel=channel,
        release_dir=release_dir,
        manifest_path=manifest_path,
        zip_path=zip_path,
        exe_sha256=exe_sha256,
        zip_sha256=final_zip_sha256,
        installer_sha256=(
            str(primary_installer["sha256"]) if primary_installer is not None else None
        ),
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=datetime.now().strftime("%Y.%m.%d"))
    parser.add_argument("--channel", default="portable")
    parser.add_argument("--license-profile", default="portable-dev")
    parser.add_argument("--installer-path", action="append")
    args = parser.parse_args()

    result = build_desktop_release_package(
        Path.cwd(),
        version=args.version,
        channel=args.channel,
        license_profile=args.license_profile,
        installer_path=args.installer_path,
    )
    print(f"desktop-release-ok: {result.zip_path}")
    print(f"manifest: {result.manifest_path}")
    print(f"exe_sha256: {result.exe_sha256}")
    print(f"zip_sha256: {result.zip_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
