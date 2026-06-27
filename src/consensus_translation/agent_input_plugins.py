from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Protocol


@dataclass(frozen=True)
class CapturedInput:
    input_ref: str
    source_type: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class InputPlugin(Protocol):
    plugin_id: str
    source_type: str

    def capture(self, **kwargs: object) -> CapturedInput:
        ...


class OcrImageInputPlugin:
    plugin_id = "ocr-image"
    source_type = "ocr"
    supported_suffixes = {
        ".bmp",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }

    def __init__(
        self,
        ocr_fn: Callable[[Path, str], str] | None = None,
        default_lang: str = "jpn+eng",
        command: str = "tesseract",
    ) -> None:
        self._ocr_fn = ocr_fn
        self.default_lang = default_lang
        self.command = command

    def capture(self, **kwargs: object) -> CapturedInput:
        if "path" not in kwargs:
            raise ValueError("ocr image path is required")
        path = Path(str(kwargs["path"]))
        suffix = path.suffix.lower()
        if suffix not in self.supported_suffixes:
            raise ValueError(f"unsupported ocr image type: {suffix}")
        lang = str(kwargs.get("lang") or self.default_lang)
        text = self._run_ocr(path, lang).strip()
        warnings = []
        if not text:
            warnings.append("ocr-empty")
        return CapturedInput(
            input_ref=str(path),
            source_type=self.source_type,
            text=text,
            metadata={"plugin_id": self.plugin_id, "lang": lang},
            warnings=warnings,
        )

    def _run_ocr(self, path: Path, lang: str) -> str:
        if self._ocr_fn is not None:
            return self._ocr_fn(path, lang)
        try:
            completed = subprocess.run(
                [self.command, str(path), "stdout", "-l", lang],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "tesseract executable not found; install Tesseract OCR or configure OCR plugin"
            ) from exc
        if completed.returncode != 0:
            message = completed.stderr.strip() or "tesseract ocr failed"
            raise RuntimeError(message)
        return completed.stdout


class HookTextBufferPlugin:
    plugin_id = "hook-buffer"
    source_type = "hook"

    def __init__(self) -> None:
        self._buffers: dict[str, list[str]] = {}

    def append_text(self, process_ref: str, text: str) -> None:
        normalized_ref = process_ref.strip() or "manual"
        if not text:
            return
        self._buffers.setdefault(normalized_ref, []).append(text)

    def capture(self, **kwargs: object) -> CapturedInput:
        process_ref = str(kwargs.get("process_ref") or "manual").strip() or "manual"
        consume = bool(kwargs.get("consume", True))
        chunks = list(self._buffers.get(process_ref, []))
        text = "\n".join(chunks)
        if consume:
            self._buffers[process_ref] = []
        warnings = []
        if not text:
            warnings.append("hook-buffer-empty")
        return CapturedInput(
            input_ref=f"hook:{process_ref}",
            source_type=self.source_type,
            text=text,
            metadata={"plugin_id": self.plugin_id, "process_ref": process_ref},
            warnings=warnings,
        )


class FolderInboxInputPlugin:
    plugin_id = "folder-inbox"
    source_type = "folder"
    supported_suffixes = {".txt", ".md", ".json"}

    def __init__(
        self,
        inbox_dir: str | Path,
        archive_dir: str | Path | None = None,
        error_dir: str | Path | None = None,
        max_payload_bytes: int = 1_000_000,
    ) -> None:
        self.inbox_dir = Path(inbox_dir)
        self.archive_dir = Path(archive_dir) if archive_dir else self.inbox_dir / "archive"
        self.error_dir = Path(error_dir) if error_dir else self.inbox_dir / "error"
        self.max_payload_bytes = max_payload_bytes
        self.state_path = self.inbox_dir / ".folder-inbox-state.json"

    def capture(self, **kwargs: object) -> list[CapturedInput]:
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        seen_hashes = self._load_seen_hashes()
        captured: list[CapturedInput] = []

        for path in sorted(self.inbox_dir.iterdir(), key=lambda item: item.name.lower()):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.parent.resolve() != self.inbox_dir.resolve():
                continue
            if path.suffix.lower() not in self.supported_suffixes:
                self._move_unique(path, self.error_dir)
                continue

            try:
                payload = path.read_bytes()
                if len(payload) > self.max_payload_bytes:
                    raise ValueError(f"payload too large: {path.name}")
                digest = hashlib.sha256(payload).hexdigest()
                if digest in seen_hashes:
                    self._move_unique(path, self.archive_dir)
                    continue
                text, metadata = self._parse_payload(path, payload)
            except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
                self._move_unique(path, self.error_dir)
                continue

            seen_hashes.add(digest)
            metadata.update(
                {
                    "plugin_id": self.plugin_id,
                    "path": str(path),
                    "sha256": digest,
                }
            )
            captured.append(
                CapturedInput(
                    input_ref=str(path),
                    source_type=self.source_type,
                    text=text,
                    metadata=metadata,
                    warnings=[],
                )
            )
            self._move_unique(path, self.archive_dir)

        self._save_seen_hashes(seen_hashes)
        return captured

    def _parse_payload(
        self,
        path: Path,
        payload: bytes,
    ) -> tuple[str, dict[str, str]]:
        if path.suffix.lower() == ".json":
            raw = json.loads(payload.decode("utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("folder inbox json payload must be an object")
            text = raw.get("text")
            if not isinstance(text, str):
                raise ValueError("folder inbox json payload requires text")
            metadata = {
                str(key): str(value)
                for key, value in raw.items()
                if key != "text" and isinstance(value, (str, int, float, bool))
            }
            return text, metadata
        return payload.decode("utf-8"), {}

    def _load_seen_hashes(self) -> set[str]:
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()
        if not isinstance(raw, dict):
            return set()
        hashes = raw.get("seen_sha256")
        if not isinstance(hashes, list):
            return set()
        return {str(item) for item in hashes}

    def _save_seen_hashes(self, seen_hashes: set[str]) -> None:
        self.state_path.write_text(
            json.dumps(
                {"seen_sha256": sorted(seen_hashes)},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    @staticmethod
    def _move_unique(path: Path, target_dir: Path) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / path.name
        if target.exists():
            stem = path.stem
            suffix = path.suffix
            index = 1
            while True:
                candidate = target_dir / f"{stem}-{index}{suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                index += 1
        shutil.move(str(path), str(target))
        return target


class InputPluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, InputPlugin] = {}

    def register(self, plugin: InputPlugin) -> None:
        self._plugins[plugin.plugin_id] = plugin

    def get(self, plugin_id: str) -> InputPlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise KeyError(f"input plugin not found: {plugin_id}") from exc

    def capture(self, plugin_id: str, **kwargs: object) -> CapturedInput:
        return self.get(plugin_id).capture(**kwargs)

    def list_plugin_ids(self) -> list[str]:
        return sorted(self._plugins)


def default_input_plugin_registry(
    tesseract_command: str = "tesseract",
    default_ocr_lang: str = "jpn+eng",
    folder_inbox: str | Path | None = None,
) -> InputPluginRegistry:
    registry = InputPluginRegistry()
    registry.register(HookTextBufferPlugin())
    if folder_inbox is not None:
        registry.register(FolderInboxInputPlugin(folder_inbox))
    registry.register(
        OcrImageInputPlugin(
            command=tesseract_command,
            default_lang=default_ocr_lang,
        )
    )
    return registry
