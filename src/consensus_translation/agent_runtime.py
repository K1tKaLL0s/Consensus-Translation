from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import shutil
import sys
from typing import Callable, Iterable


WhichFn = Callable[[str], str | None]


def _resolve_configured_path(value: str | Path, base: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


@dataclass(frozen=True)
class RuntimeLayout:
    install_root: Path
    runtime_root: Path
    data_root: Path
    tesseract_command: Path
    comet_command: Path
    comet_model_root: Path

    @classmethod
    def from_roots(
        cls,
        install_root: str | Path,
        data_root: str | Path | None = None,
    ) -> "RuntimeLayout":
        install = Path(install_root).resolve()
        runtime = (install / "runtime").resolve()
        data = (
            Path(data_root).resolve()
            if data_root is not None
            else (install / "data").resolve()
        )
        return cls(
            install_root=install,
            runtime_root=runtime,
            data_root=data,
            tesseract_command=(
                runtime / "Tesseract-OCR" / "tesseract.exe"
            ).resolve(),
            comet_command=(
                runtime / "comet-score.cmd"
            ).resolve(),
            comet_model_root=(runtime / "comet-models").resolve(),
        )

    @classmethod
    def discover(
        cls,
        project_root: str | Path | None = None,
        install_root: str | Path | None = None,
        data_root: str | Path | None = None,
    ) -> "RuntimeLayout":
        if install_root is not None:
            return cls.from_roots(install_root, data_root)

        root = (
            Path(project_root).resolve()
            if project_root is not None
            else Path.cwd().resolve()
        )
        settings = load_runtime_settings(root)
        if settings:
            runtime = _resolve_configured_path(
                settings.get("runtime_root", root / ".runtime"),
                root,
            )
            data = (
                Path(data_root).resolve()
                if data_root is not None
                else (root / "data").resolve()
            )
            return cls(
                install_root=root,
                runtime_root=runtime,
                data_root=data,
                tesseract_command=_resolve_configured_path(
                    settings.get(
                        "tesseract_command",
                        runtime / "Tesseract-OCR" / "tesseract.exe",
                    ),
                    root,
                ),
                comet_command=_resolve_configured_path(
                    settings.get(
                        "comet_command",
                        runtime / "comet-score.cmd",
                    ),
                    root,
                ),
                comet_model_root=_resolve_configured_path(
                    settings.get(
                        "comet_model_storage_path",
                        runtime / "comet-models",
                    ),
                    root,
                ),
            )

        if getattr(sys, "frozen", False):
            executable_dir = Path(sys.executable).resolve().parent
            packaged_root = (
                executable_dir.parent
                if (executable_dir.parent / "runtime").exists()
                else executable_dir
            )
            return cls.from_roots(packaged_root, data_root)

        runtime = (root / ".runtime").resolve()
        data = (
            Path(data_root).resolve()
            if data_root is not None
            else (root / "data").resolve()
        )
        return cls(
            install_root=root,
            runtime_root=runtime,
            data_root=data,
            tesseract_command=(
                runtime / "Tesseract-OCR" / "tesseract.exe"
            ).resolve(),
            comet_command=(
                runtime / "comet-score.cmd"
            ).resolve(),
            comet_model_root=(runtime / "comet-models").resolve(),
        )


def _deduplicate(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path).casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _runtime_root(project_root: str | Path | None) -> Path:
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    return root / ".runtime"


def _runtime_roots(project_root: str | Path | None) -> list[Path]:
    roots: list[Path] = []
    if project_root is not None:
        roots.append(Path(project_root).resolve())
    roots.append(Path.cwd().resolve())
    executable_dir = Path(sys.executable).resolve().parent
    roots.extend([executable_dir, executable_dir.parent])
    return [path / ".runtime" for path in _deduplicate(roots)]


def load_runtime_settings(
    project_root: str | Path | None = None,
) -> dict[str, str]:
    for runtime_root in _runtime_roots(project_root):
        path = runtime_root / "runtime-settings.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        return {
            str(key): str(value)
            for key, value in payload.items()
            if value is not None
        }
    return {}


def default_tesseract_candidates(
    project_root: str | Path | None = None,
) -> list[Path]:
    return _deduplicate(
        [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Tesseract-OCR\tesseract.exe"),
            Path(r"E:\Tesseract-OCR\tesseract.exe"),
            Path(r"E:\Tools\Tesseract-OCR\tesseract.exe"),
            Path(r"E:\ConsensusTranslationRuntime\Tesseract-OCR\tesseract.exe"),
            *[
                root / "Tesseract-OCR" / "tesseract.exe"
                for root in _runtime_roots(project_root)
            ],
        ]
    )


def default_comet_candidates(
    project_root: str | Path | None = None,
) -> list[Path]:
    local_app_data = os.getenv("LOCALAPPDATA")
    candidates = [
        Path(r"C:\ConsensusTranslationRuntime\comet-score.cmd"),
        Path(r"C:\ConsensusTranslationRuntime\comet-env\Scripts\comet-score.exe"),
    ]
    if local_app_data:
        candidates.append(
            Path(local_app_data)
            / "ConsensusTranslation"
            / "runtime"
            / "comet-score.cmd"
        )
        candidates.append(
            Path(local_app_data)
            / "ConsensusTranslation"
            / "runtime"
            / "comet-env"
            / "Scripts"
            / "comet-score.exe"
        )
    candidates.extend(
        [
            Path(r"E:\ConsensusTranslationRuntime\comet-score.cmd"),
            Path(r"E:\ConsensusTranslationRuntime\comet-env\Scripts\comet-score.exe"),
            Path(r"E:\Tools\comet-score.cmd"),
            Path(r"E:\Tools\comet-env\Scripts\comet-score.exe"),
            *[
                root / "comet-score.cmd"
                for root in _runtime_roots(project_root)
            ],
            *[
                root / "comet-env" / "Scripts" / "comet-score.exe"
                for root in _runtime_roots(project_root)
            ],
        ]
    )
    return _deduplicate(candidates)


def _resolve_command(
    configured: str | None,
    executable_name: str,
    candidate_paths: Iterable[Path],
    which_fn: WhichFn,
) -> str:
    configured_value = (configured or "").strip()
    if configured_value:
        return configured_value
    for candidate in candidate_paths:
        if candidate.is_file():
            return str(candidate)
    discovered = which_fn(executable_name)
    return discovered or executable_name


def resolve_tesseract_command(
    configured: str | None = None,
    project_root: str | Path | None = None,
    candidate_paths: Iterable[Path] | None = None,
    which_fn: WhichFn = shutil.which,
) -> str:
    settings = load_runtime_settings(project_root)
    return _resolve_command(
        configured=configured or settings.get("tesseract_command"),
        executable_name="tesseract",
        candidate_paths=(
            list(candidate_paths)
            if candidate_paths is not None
            else default_tesseract_candidates(project_root)
        ),
        which_fn=which_fn,
    )


def resolve_comet_command(
    configured: str | None = None,
    project_root: str | Path | None = None,
    candidate_paths: Iterable[Path] | None = None,
    which_fn: WhichFn = shutil.which,
) -> str:
    settings = load_runtime_settings(project_root)
    return _resolve_command(
        configured=configured or settings.get("comet_command"),
        executable_name="comet-score",
        candidate_paths=(
            list(candidate_paths)
            if candidate_paths is not None
            else default_comet_candidates(project_root)
        ),
        which_fn=which_fn,
    )


def resolve_comet_model_storage_path(
    configured: str | None,
    comet_command: str,
    project_root: str | Path | None = None,
) -> str:
    configured_value = (configured or "").strip()
    if configured_value:
        return configured_value
    command_path = Path(comet_command)
    if command_path.is_absolute() and command_path.name.lower() == "comet-score.cmd":
        return str(command_path.parent / "comet-models")
    if command_path.is_absolute() and len(command_path.parents) >= 3:
        return str(command_path.parents[2] / "comet-models")
    settings = load_runtime_settings(project_root)
    settings_value = settings.get("comet_model_storage_path", "").strip()
    if settings_value:
        return settings_value
    return str(_runtime_root(project_root) / "comet-models")
