from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DesktopProjectProfile:
    project_id: str = "default"
    source_lang: str = "zh"
    target_lang: str = "ja"
    topic: str = "general"
    mode: str = "learning"
    max_context_tokens: int = 4096
    reserved_output_tokens: int = 1024
    api_enabled: bool = False
    budget_limit: float = 0.0
    require_remote_confirmation: bool = True
    allow_training_upload: bool = False
    training_file: str = ""
    validation_file: str = ""
    evaluator_kind: str = "deterministic"
    tesseract_command: str = ""
    ocr_language: str = "jpn+eng"
    comet_command: str = ""
    comet_model: str = "Unbabel/wmt22-comet-da"
    comet_model_storage_path: str = ""
    recent_files: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "topic": self.topic,
            "mode": self.mode,
            "max_context_tokens": self.max_context_tokens,
            "reserved_output_tokens": self.reserved_output_tokens,
            "api_enabled": self.api_enabled,
            "budget_limit": self.budget_limit,
            "require_remote_confirmation": self.require_remote_confirmation,
            "allow_training_upload": self.allow_training_upload,
            "training_file": self.training_file,
            "validation_file": self.validation_file,
            "evaluator_kind": self.evaluator_kind,
            "tesseract_command": self.tesseract_command,
            "ocr_language": self.ocr_language,
            "comet_command": self.comet_command,
            "comet_model": self.comet_model,
            "comet_model_storage_path": self.comet_model_storage_path,
            "recent_files": list(self.recent_files),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, object]) -> "DesktopProjectProfile":
        recent_files = data.get("recent_files", [])
        if not isinstance(recent_files, list):
            recent_files = []
        return cls(
            project_id=str(data.get("project_id", "default")),
            source_lang=str(data.get("source_lang", "zh")),
            target_lang=str(data.get("target_lang", "ja")),
            topic=str(data.get("topic", "general")),
            mode=str(data.get("mode", "learning")),
            max_context_tokens=int(data.get("max_context_tokens", 4096)),
            reserved_output_tokens=int(data.get("reserved_output_tokens", 1024)),
            api_enabled=bool(data.get("api_enabled", False)),
            budget_limit=float(data.get("budget_limit", 0.0)),
            require_remote_confirmation=bool(
                data.get("require_remote_confirmation", True)
            ),
            allow_training_upload=bool(data.get("allow_training_upload", False)),
            training_file=str(data.get("training_file", "")),
            validation_file=str(data.get("validation_file", "")),
            evaluator_kind=str(data.get("evaluator_kind", "deterministic")),
            tesseract_command=str(data.get("tesseract_command", "")),
            ocr_language=str(data.get("ocr_language", "jpn+eng")),
            comet_command=str(data.get("comet_command", "")),
            comet_model=str(
                data.get("comet_model", "Unbabel/wmt22-comet-da")
            ),
            comet_model_storage_path=str(
                data.get("comet_model_storage_path", "")
            ),
            recent_files=[str(item) for item in recent_files],
        )
