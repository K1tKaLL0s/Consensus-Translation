from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from consensus_translation.desktop_qt.i18n import default_interface_language
from consensus_translation.services.translation.types import (
    SUPPORTED_TRANSLATION_LANGUAGES,
    TARGET_TRANSLATION_LANGUAGES,
)


CONTROLLED_WORKFLOW_MODES: tuple[str, ...] = (
    "local",
    "ai_assisted",
    "learning",
    "self_iterative",
    "self_decision",
    "pretraining",
)


@dataclass(frozen=True)
class UserSettings:
    interface_language: str = "en-US"
    auto_save_history: bool = True
    default_source_language: str = "auto"
    default_target_language: str = "ja"
    default_mode: str = "local"
    budget_limit: float = 0.0
    allow_glossary_suggestions: bool = True

    def with_changes(
        self,
        *,
        interface_language: str | None = None,
        auto_save_history: bool | None = None,
        default_source_language: str | None = None,
        default_target_language: str | None = None,
        default_mode: str | None = None,
        budget_limit: float | None = None,
        allow_glossary_suggestions: bool | None = None,
    ) -> "UserSettings":
        return UserSettings(
            interface_language=interface_language or self.interface_language,
            auto_save_history=(
                self.auto_save_history
                if auto_save_history is None
                else auto_save_history
            ),
            default_source_language=normalize_source_language(
                default_source_language or self.default_source_language
            ),
            default_target_language=normalize_target_language(
                default_target_language or self.default_target_language
            ),
            default_mode=normalize_workflow_mode(default_mode or self.default_mode),
            budget_limit=(
                self.budget_limit if budget_limit is None else max(0.0, float(budget_limit))
            ),
            allow_glossary_suggestions=(
                self.allow_glossary_suggestions
                if allow_glossary_suggestions is None
                else allow_glossary_suggestions
            ),
        )


class UserSettingsStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, browser_language: str | None = None) -> UserSettings:
        defaults = UserSettings(
            interface_language=default_interface_language(browser_language),
            auto_save_history=True,
        )
        if not self.path.is_file():
            return defaults
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        if not isinstance(payload, dict):
            return defaults
        return UserSettings(
            interface_language=str(
                payload.get(
                    "interface_language",
                    default_interface_language(browser_language),
                )
            ),
            auto_save_history=_bool_setting(payload.get("auto_save_history"), True),
            default_source_language=normalize_source_language(
                payload.get("default_source_language", defaults.default_source_language)
            ),
            default_target_language=normalize_target_language(
                payload.get("default_target_language", defaults.default_target_language)
            ),
            default_mode=normalize_workflow_mode(
                payload.get("default_mode", defaults.default_mode)
            ),
            budget_limit=_float_setting(payload.get("budget_limit"), 0.0),
            allow_glossary_suggestions=_bool_setting(
                payload.get("allow_glossary_suggestions"),
                True,
            ),
        )

    def save(self, settings: UserSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def normalize_source_language(value: object) -> str:
    language = str(value or "auto")
    if language in SUPPORTED_TRANSLATION_LANGUAGES:
        return language
    return "auto"


def normalize_target_language(value: object) -> str:
    language = str(value or "ja")
    if language in TARGET_TRANSLATION_LANGUAGES:
        return language
    return "ja"


def normalize_workflow_mode(value: object) -> str:
    mode = str(value or "local")
    if mode in CONTROLLED_WORKFLOW_MODES:
        return mode
    return "local"


def _float_setting(value: object, default: float) -> float:
    try:
        return max(0.0, float(str(value)))
    except (TypeError, ValueError):
        return default


def _bool_setting(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)