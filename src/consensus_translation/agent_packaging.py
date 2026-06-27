from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class DesktopPackagingPreflight:
    ok: bool
    variant: str
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
    variant: str = "tkinter",
) -> DesktopPackagingPreflight:
    root = Path(project_root).resolve()
    if variant == "tkinter":
        entrypoint_path = root / "src" / "consensus_translation" / "desktop_agent_app.py"
        spec_path = root / "packaging" / "desktop_agent.spec"
        build_script_path = root / "build_desktop_agent.ps1"
    elif variant == "qt":
        entrypoint_path = (
            root / "src" / "consensus_translation" / "desktop_qt" / "application.py"
        )
        spec_path = root / "packaging" / "desktop_agent_qt.spec"
        build_script_path = root / "build_desktop_qt.ps1"
    else:
        raise ValueError(f"unsupported desktop packaging variant: {variant}")
    requirements_path = root / "requirements-desktop.txt"

    missing: list[str] = []
    _exists_or_missing(entrypoint_path, "desktop-entrypoint", missing)
    _exists_or_missing(spec_path, "pyinstaller-spec", missing)
    _exists_or_missing(build_script_path, "build-script", missing)
    _exists_or_missing(requirements_path, "desktop-requirements", missing)

    if import_checker("PyInstaller") is None:
        missing.append("pyinstaller")
    if variant == "qt" and import_checker("PySide6") is None:
        missing.append("pyside6")

    actions: list[str] = []
    if "pyinstaller" in missing:
        actions.append("python -m pip install -r requirements-desktop.txt")
    if "pyside6" in missing:
        actions.append(
            "python -m pip install -r requirements-qt.txt --target .runtime\\python-packages-qt"
        )
    if "desktop-entrypoint" in missing:
        if variant == "qt":
            actions.append("restore src/consensus_translation/desktop_qt/application.py")
        else:
            actions.append("restore src/consensus_translation/desktop_agent_app.py")
    if "pyinstaller-spec" in missing:
        if variant == "qt":
            actions.append("restore packaging/desktop_agent_qt.spec")
        else:
            actions.append("restore packaging/desktop_agent.spec")
    if "build-script" in missing:
        if variant == "qt":
            actions.append("restore build_desktop_qt.ps1")
        else:
            actions.append("restore build_desktop_agent.ps1")
    if "desktop-requirements" in missing:
        actions.append("restore requirements-desktop.txt")

    return DesktopPackagingPreflight(
        ok=not missing,
        variant=variant,
        entrypoint_path=entrypoint_path,
        spec_path=spec_path,
        build_script_path=build_script_path,
        requirements_path=requirements_path,
        missing=missing,
        actions=actions,
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("tkinter", "qt"), default="tkinter")
    args = parser.parse_args()

    root = Path.cwd()
    result = check_desktop_packaging_ready(root, variant=args.variant)
    if result.ok:
        print(f"desktop-packaging-preflight-ok:{result.variant}")
        return 0
    print(f"desktop-packaging-preflight-failed:{result.variant}")
    for item in result.missing:
        print(f"missing: {item}")
    for action in result.actions:
        print(f"action: {action}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
