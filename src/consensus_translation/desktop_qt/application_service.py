from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys
from typing import Iterable

from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_diagnostics import format_diagnostic_lines
from consensus_translation.agent_provider_smoke import format_provider_smoke_lines
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.agent_inputs import load_agent_input
from consensus_translation.agent_continuation import ContextManagedTranslationResult
from consensus_translation.desktop_agent_app import (
    DesktopAgentController,
    DesktopAgentConfig,
    default_desktop_credentials_path,
    default_desktop_store_path,
    format_remote_preflight_lines,
)
from consensus_translation.desktop_qt.history_store import (
    TranslationHistoryRecord,
    TranslationHistoryStore,
)
from consensus_translation.desktop_qt.settings_store import (
    UserSettings,
    UserSettingsStore,
)
from consensus_translation.services.finalize_service import FinalizeService


@dataclass(frozen=True)
class TranslationViewResult:
    final_text: str
    status_label: str
    run_id: str
    candidates: tuple[str, ...]


class DesktopApplicationService:
    """Qt-facing boundary around the desktop agent controller."""

    def __init__(
        self,
        controller: DesktopAgentController | None = None,
        credential_store: LocalCredentialStore | None = None,
        data_root: str | Path | None = None,
    ) -> None:
        self.data_root = Path(data_root).resolve() if data_root else default_desktop_store_path().parent
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.credential_store = credential_store or LocalCredentialStore(
            self.data_root / "credentials.json"
            if data_root is not None
            else default_desktop_credentials_path()
        )
        self.settings_store = UserSettingsStore(self.data_root / "user_settings.json")
        self.history_store = TranslationHistoryStore(
            self.data_root / "translation_history.json"
        )
        self.controller = controller or DesktopAgentController(
            store=AgentRunStore(self.data_root / "agent.sqlite3")
            if data_root is not None
            else AgentRunStore(default_desktop_store_path())
        )
        self.finalize_service = FinalizeService(
            agent_store=self.controller.store,
            lexicon_store=self.controller.lexicon_store or self.controller.store,
            history_store=self.history_store,
        )
        self._last_translation: ContextManagedTranslationResult | None = None

    @classmethod
    def from_existing(
        cls,
        candidate: object | None,
        data_root: str | Path | None = None,
    ) -> "DesktopApplicationService":
        if isinstance(candidate, cls):
            return candidate
        if isinstance(candidate, DesktopAgentController):
            return cls(controller=candidate, data_root=data_root)
        return cls(data_root=data_root)

    def translate_text(
        self,
        text: str,
        *,
        source_lang: str | None = None,
        target_lang: str | None = None,
        topic: str | None = None,
        mode: str | None = None,
        evaluator_kind: str | None = None,
        api_enabled: bool | None = None,
        budget_limit: float | None = None,
        training_file: str | None = None,
        validation_file: str | None = None,
        allow_training_upload: bool | None = None,
    ) -> TranslationViewResult:
        self._update_config(
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
            mode=mode,
            evaluator_kind=evaluator_kind,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
            training_file=training_file,
            validation_file=validation_file,
            allow_training_upload=allow_training_upload,
        )
        result = self.controller.translate_text(text.strip())
        self._last_translation = result
        if self.load_user_settings().auto_save_history:
            self._save_history_for_result(text.strip(), result)
        run = result.initial_task.run
        run_id = run.contract.run_id if run is not None else ""
        status = run.contract.status.value if run is not None else str(result.verification.get("status", ""))
        candidates = tuple(
            f"{candidate.provider_id} | confidence={candidate.confidence:.2f} | {candidate.text[:80]}"
            for candidate in (run.candidates if run is not None else [])
        )
        return TranslationViewResult(
            final_text=result.final_text,
            status_label=self._status_label(status),
            run_id=run_id,
            candidates=candidates,
        )

    def load_source_file(self, path: str | Path) -> str:
        document = load_agent_input(path)
        self.controller.record_recent_file(path)
        return document.text

    def preview_remote_calls(
        self,
        text: str,
        **config_updates: object,
    ) -> list[str]:
        self._update_config(**config_updates)
        return format_remote_preflight_lines(
            self.controller.preview_remote_calls(text.strip())
        )

    def confirm_remote_preflight(
        self,
        text: str,
        **config_updates: object,
    ) -> str:
        self._update_config(**config_updates)
        return self.controller.confirm_remote_preflight(text.strip())

    def export_last_translation(
        self,
        output_dir: str | Path,
        base_name: str = "translation",
    ) -> dict[str, Path]:
        if self._last_translation is None:
            raise ValueError("no translation result to export")
        return self.controller.export_translation_artifacts(
            self._last_translation,
            output_dir=output_dir,
            base_name=base_name,
        )

    def load_user_settings(
        self,
        browser_language: str | None = None,
    ) -> UserSettings:
        return self.settings_store.load(browser_language=browser_language)

    def save_user_settings(self, settings: UserSettings) -> None:
        self.settings_store.save(settings)

    def save_translation_history(
        self,
        *,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        topic: str = "",
        mode: str = "",
        run_id: str = "",
        workflow_status: str = "",
        workflow_steps: tuple[str, ...] = (),
        consensus_score: float | None = None,
        confidence_level: str = "",
        conflicts: tuple[str, ...] = (),
        arbitration_reason: str = "",
        requires_human_review: bool = False,
        rating: int | None = None,
        rating_issue_tags: tuple[str, ...] = (),
        rating_comment: str = "",
    ) -> TranslationHistoryRecord:
        return self.finalize_service.commit_translation_history(
            source_text=source_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            topic=topic,
            mode=mode,
            run_id=run_id,
            workflow_status=workflow_status,
            workflow_steps=workflow_steps,
            consensus_score=consensus_score,
            confidence_level=confidence_level,
            conflicts=conflicts,
            arbitration_reason=arbitration_reason,
            requires_human_review=requires_human_review,
            rating=rating,
            rating_issue_tags=rating_issue_tags,
            rating_comment=rating_comment,
        )

    def _save_history_for_result(
        self,
        source_text: str,
        result: ContextManagedTranslationResult,
    ) -> None:
        run = result.initial_task.run
        if run is None:
            self.save_translation_history(
                source_text=source_text,
                translated_text=result.final_text,
                source_language=self.controller.config.source_lang,
                target_language=self.controller.config.target_lang,
                topic=self.controller.config.topic,
                mode=self.controller.config.mode,
            )
            return
        workflow_steps = tuple(
            item for item in run.contract.trace if str(item).startswith("workflow:")
        )
        self.save_translation_history(
            source_text=source_text,
            translated_text=result.final_text,
            source_language=self.controller.config.source_lang,
            target_language=self.controller.config.target_lang,
            topic=self.controller.config.topic,
            mode=self.controller.config.mode,
            run_id=run.contract.run_id,
            workflow_status=run.contract.status.value,
            workflow_steps=workflow_steps,
            consensus_score=run.decision.final_score,
            confidence_level=run.decision.confidence_level,
            conflicts=tuple(run.decision.conflict_points),
            arbitration_reason=run.decision.arbitration_reason,
            requires_human_review=run.decision.requires_human_review,
        )

    def submit_translation_rating(
        self,
        *,
        source_text: str,
        final_translation: str,
        rating: int,
        issue_tags: tuple[str, ...] = (),
        dimension_scores: dict[str, float] | None = None,
        comment: str = "",
    ):
        if self._last_translation is None or self._last_translation.initial_task.run is None:
            raise ValueError("no translation run to rate")
        run = self._last_translation.initial_task.run
        return self.finalize_service.submit_rating(
            run=run,
            mode=self.controller.config.mode,
            source_language=self.controller.config.source_lang,
            target_language=self.controller.config.target_lang,
            topic=self.controller.config.topic,
            source_text=source_text,
            final_translation=final_translation,
            rating=rating,
            issue_tags=tuple(issue_tags),
            dimension_scores=dimension_scores,
            comment=comment,
        )

    def skip_translation_rating(self, run_id: str) -> None:
        return self.finalize_service.skip_rating(run_id)

    def list_translation_history(self) -> list[TranslationHistoryRecord]:
        return self.history_store.list_recent()

    def clear_translation_history(self) -> None:
        self.history_store.clear()

    def list_runs(self) -> list[dict[str, object]]:
        return self.controller.list_audit_runs()

    def confirm_run(self, run_id: str) -> bool:
        return self.finalize_service.confirm_run(run_id)

    def list_pending_lexicon_updates(self) -> list[dict[str, object]]:
        return self.controller.list_pending_lexicon_updates()

    def confirm_lexicon_update(self, event_id: int) -> bool:
        return self.finalize_service.confirm_lexicon_update(event_id)

    def export_current_topic_lexicon(self) -> dict[str, dict[str, str]]:
        return self.controller.export_topic_lexicon(self.controller.config.topic)

    def export_lexicon_to_file(self, path: str | Path) -> Path:
        return self.finalize_service.export_lexicon_to_file(path)

    def import_lexicon_from_file(self, path: str | Path) -> dict[str, int]:
        return self.finalize_service.import_lexicon_from_file(path)

    def save_provider_settings(
        self,
        *,
        provider_id: str,
        base_url: str,
        model: str,
        api_key: str,
        estimated_cost: float = 0.0,
        enabled: bool = True,
    ):
        return self.controller.save_provider_settings(
            credential_store=self.credential_store,
            provider_id=provider_id,
            base_url=base_url,
            model=model,
            api_key=api_key,
            estimated_cost=estimated_cost,
            enabled=enabled,
        )

    def list_provider_configs(self) -> list[object]:
        store = self.controller.store
        if store is None or not hasattr(store, "list_provider_configs"):
            return []
        return list(store.list_provider_configs())

    def load_enabled_providers(self) -> list[object]:
        return self.controller.load_enabled_provider_configs(self.credential_store)

    def smoke_test_providers(self, sample_text: str = "hello") -> list[str]:
        results = self.controller.smoke_test_providers(sample_text=sample_text)
        return format_provider_smoke_lines(results)

    def run_diagnostics(self, mode: str | None = None) -> list[str]:
        diagnostic_mode = mode or ("installed" if getattr(sys, "frozen", False) else "developer")
        report = self.controller.run_diagnostics(
            credential_store=self.credential_store,
            mode=diagnostic_mode,
        )
        return format_diagnostic_lines(report)

    def run_local_acceptance(self) -> list[str]:
        result = self.controller.run_local_acceptance(
            self.data_root / "acceptance"
        )
        return [
            f"ok={result.ok}",
            f"verification={result.verification.get('status')}",
            f"artifacts={len(result.artifacts)}",
        ]

    def project_summary_lines(self) -> list[str]:
        profile = self.controller.load_project_profile()
        if profile is None:
            return [
                f"项目：{self.controller.project_id}",
                f"语言：{self.controller.config.source_lang} → {self.controller.config.target_lang}",
                "尚未保存项目配置",
            ]
        return [
            f"项目：{profile.project_id}",
            f"语言：{profile.source_lang} → {profile.target_lang}",
            f"题材：{profile.topic}",
            f"最近文件：{len(profile.recent_files)}",
        ]

    def _update_config(self, **updates: object) -> None:
        clean = {
            key: value
            for key, value in updates.items()
            if value is not None and value != ""
        }
        if clean:
            self.controller.config = replace(self.controller.config, **clean)

    @staticmethod
    def _status_label(status: str) -> str:
        if status == "finalized":
            return "已完成"
        if status in {"awaiting_human_confirmation", "needs_review"}:
            return "等待人工确认"
        if status == "budget_exceeded":
            return "预算不足"
        return status or "已完成"


def join_lines(lines: Iterable[object]) -> str:
    return "\n".join(str(line) for line in lines)
