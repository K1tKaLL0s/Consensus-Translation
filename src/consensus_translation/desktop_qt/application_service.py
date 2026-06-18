from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_diagnostics import format_diagnostic_lines
from consensus_translation.agent_provider_smoke import format_provider_smoke_lines
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.agent_inputs import load_agent_input
from consensus_translation.desktop_agent_app import (
    DesktopAgentController,
    DesktopAgentConfig,
    default_desktop_credentials_path,
    default_desktop_store_path,
    format_remote_preflight_lines,
)


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
        self.controller = controller or DesktopAgentController(
            store=AgentRunStore(self.data_root / "agent.sqlite3")
            if data_root is not None
            else AgentRunStore(default_desktop_store_path())
        )
        self._last_translation = None

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

    def list_runs(self) -> list[dict[str, object]]:
        return self.controller.list_audit_runs()

    def confirm_run(self, run_id: str) -> bool:
        return self.controller.confirm_run(run_id)

    def list_pending_lexicon_updates(self) -> list[dict[str, object]]:
        return self.controller.list_pending_lexicon_updates()

    def confirm_lexicon_update(self, event_id: int) -> bool:
        return self.controller.confirm_lexicon_update(event_id)

    def export_current_topic_lexicon(self) -> dict[str, dict[str, str]]:
        return self.controller.export_topic_lexicon(self.controller.config.topic)

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

    def run_diagnostics(self, mode: str = "developer") -> list[str]:
        report = self.controller.run_diagnostics(
            credential_store=self.credential_store,
            mode=mode,
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
