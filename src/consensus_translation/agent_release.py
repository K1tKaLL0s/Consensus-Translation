from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

    actions: list[str] = []
    if "desktop-dist" in missing or "desktop-exe" in missing:
        actions.append("powershell -ExecutionPolicy Bypass -File .\\build_desktop_agent.ps1")
    if "readme" in missing:
        actions.append("restore README.md")
    if "runtime-installer" in missing:
        actions.append("restore install_optional_runtimes.ps1")

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

    manifest = {
        "app_name": "ConsensusTranslationAgent",
        "version": version,
        "channel": channel,
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
        "not_included": ["code-signing", "installer", "auto-update"],
    }
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
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=datetime.now().strftime("%Y.%m.%d"))
    parser.add_argument("--channel", default="portable")
    args = parser.parse_args()

    result = build_desktop_release_package(
        Path.cwd(),
        version=args.version,
        channel=args.channel,
    )
    print(f"desktop-release-ok: {result.zip_path}")
    print(f"manifest: {result.manifest_path}")
    print(f"exe_sha256: {result.exe_sha256}")
    print(f"zip_sha256: {result.zip_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
