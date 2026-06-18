from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class DesktopPackagingPreflight:
    ok: bool
    entrypoint_path: Path
    spec_path: Path
    build_script_path: Path
    requirements_path: Path
    missing: list[str]
    actions: list[str]


def _exists_or_missing(path: Path, label: str, missing: list[str]) -> None:
    if not path.exists():
        missing.append(label)


def check_desktop_packaging_ready(
    project_root: str | Path,
    import_checker: Callable[[str], object | None] = find_spec,
) -> DesktopPackagingPreflight:
    root = Path(project_root).resolve()
    entrypoint_path = root / "src" / "consensus_translation" / "desktop_agent_app.py"
    spec_path = root / "packaging" / "desktop_agent.spec"
    build_script_path = root / "build_desktop_agent.ps1"
    requirements_path = root / "requirements-desktop.txt"

    missing: list[str] = []
    _exists_or_missing(entrypoint_path, "desktop-entrypoint", missing)
    _exists_or_missing(spec_path, "pyinstaller-spec", missing)
    _exists_or_missing(build_script_path, "build-script", missing)
    _exists_or_missing(requirements_path, "desktop-requirements", missing)

    if import_checker("PyInstaller") is None:
        missing.append("pyinstaller")

    actions: list[str] = []
    if "pyinstaller" in missing:
        actions.append("python -m pip install -r requirements-desktop.txt")
    if "desktop-entrypoint" in missing:
        actions.append("restore src/consensus_translation/desktop_agent_app.py")
    if "pyinstaller-spec" in missing:
        actions.append("restore packaging/desktop_agent.spec")
    if "build-script" in missing:
        actions.append("restore build_desktop_agent.ps1")
    if "desktop-requirements" in missing:
        actions.append("restore requirements-desktop.txt")

    return DesktopPackagingPreflight(
        ok=not missing,
        entrypoint_path=entrypoint_path,
        spec_path=spec_path,
        build_script_path=build_script_path,
        requirements_path=requirements_path,
        missing=missing,
        actions=actions,
    )


def main() -> int:
    root = Path.cwd()
    result = check_desktop_packaging_ready(root)
    if result.ok:
        print("desktop-packaging-preflight-ok")
        return 0
    print("desktop-packaging-preflight-failed")
    for item in result.missing:
        print(f"missing: {item}")
    for action in result.actions:
        print(f"action: {action}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
