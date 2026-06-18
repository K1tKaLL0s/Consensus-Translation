from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

from consensus_translation.agent_acceptance import (
    LocalAcceptanceResult,
    acceptance_report_payload,
    format_acceptance_lines,
    run_local_acceptance,
    write_acceptance_report,
)
from consensus_translation.agent_artifacts import export_translation_artifacts
from consensus_translation.agent_context import ContextBudget
from consensus_translation.agent_continuation import (
    ContextManagedTranslationResult,
    run_context_managed_translation,
)
from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_diagnostics import (
    CommandRunner,
    DiagnosticReport,
    ImportChecker,
    diagnostic_report_payload,
    format_diagnostic_lines,
    run_desktop_diagnostics,
    write_diagnostic_report,
)
from consensus_translation.agent_evaluators import (
    ExternalCometTranslationEvaluator,
    TranslationEvaluator,
)
from consensus_translation.agent_input_plugins import (
    CapturedInput,
    HookTextBufferPlugin,
    InputPluginRegistry,
    OcrImageInputPlugin,
    default_input_plugin_registry,
)
from consensus_translation.agent_inputs import load_agent_input
from consensus_translation.agent_preflight import (
    RemoteCallPreflight,
    build_remote_call_preflight,
)
from consensus_translation.agent_project import DesktopProjectProfile
from consensus_translation.agent_provider_config import ProviderConfig, build_enabled_providers
from consensus_translation.agent_provider_smoke import (
    ProviderSmokeResult,
    format_provider_smoke_lines,
    smoke_test_provider,
)
from consensus_translation.agent_providers import EchoModelProvider, ModelProvider
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.agent_runtime import (
    RuntimeLayout,
    resolve_comet_command,
    resolve_comet_model_storage_path,
    resolve_tesseract_command,
)


@dataclass(frozen=True)
class DesktopAgentConfig:
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


class DesktopAgentController:
    def __init__(
        self,
        config: DesktopAgentConfig | None = None,
        providers: list[ModelProvider] | None = None,
        evaluator: TranslationEvaluator | None = None,
        store: object | None = None,
        lexicon_store: object | None = None,
        input_plugins: InputPluginRegistry | None = None,
        project_id: str = "default",
        runtime_layout: RuntimeLayout | None = None,
    ) -> None:
        self.config = config or DesktopAgentConfig()
        self.runtime_layout = runtime_layout or RuntimeLayout.discover(
            project_root=self._project_root()
        )
        self.providers = providers or [EchoModelProvider("desktop-preview", prefix="")]
        self.evaluator = evaluator
        self.store = store
        self.lexicon_store = lexicon_store or store
        self.input_plugins = input_plugins or default_input_plugin_registry(
            tesseract_command=self._resolved_tesseract_command(),
            default_ocr_lang=self.config.ocr_language,
        )
        self.project_id = project_id
        self._remote_confirmation_id: str | None = None

    def _context_budget(self) -> ContextBudget:
        return ContextBudget(
            max_context_tokens=self.config.max_context_tokens,
            reserved_output_tokens=self.config.reserved_output_tokens,
        )

    @staticmethod
    def _project_root() -> Path:
        return Path(__file__).resolve().parents[2]

    def _resolved_tesseract_command(self) -> str:
        if self.config.tesseract_command.strip():
            return self.config.tesseract_command.strip()
        if self.runtime_layout.tesseract_command.is_file():
            return str(self.runtime_layout.tesseract_command)
        return resolve_tesseract_command(
            project_root=self.runtime_layout.install_root,
        )

    def _resolved_comet_command(self) -> str:
        if self.config.comet_command.strip():
            return self.config.comet_command.strip()
        if self.runtime_layout.comet_command.is_file():
            return str(self.runtime_layout.comet_command)
        return resolve_comet_command(
            project_root=self.runtime_layout.install_root,
        )

    def _resolved_comet_model_storage_path(self) -> str:
        if self.config.comet_model_storage_path.strip():
            return self.config.comet_model_storage_path.strip()
        if self.config.comet_command.strip():
            return resolve_comet_model_storage_path(
                None,
                self.config.comet_command.strip(),
                project_root=self.runtime_layout.install_root,
            )
        return str(self.runtime_layout.comet_model_root)

    def _active_evaluator(self) -> TranslationEvaluator | None:
        if self.evaluator is not None:
            return self.evaluator
        if self.config.evaluator_kind.strip().lower() != "comet":
            return None
        return ExternalCometTranslationEvaluator(
            command=self._resolved_comet_command(),
            model_name=(
                self.config.comet_model.strip() or "Unbabel/wmt22-comet-da"
            ),
            model_storage_path=(
                self._resolved_comet_model_storage_path()
            ),
        )

    @staticmethod
    def _load_optional_project_text(path_text: str, label: str) -> str | None:
        normalized = path_text.strip()
        if not normalized:
            return None
        path = Path(normalized)
        if not path.is_file():
            raise ValueError(f"{label} file not found: {path}")
        return load_agent_input(path).text

    def preview_remote_calls(self, text: str) -> RemoteCallPreflight:
        training_text = self._load_optional_project_text(
            self.config.training_file,
            "training",
        )
        validation_text = self._load_optional_project_text(
            self.config.validation_file,
            "validation",
        )
        return build_remote_call_preflight(
            text=text,
            mode=self.config.mode,
            providers=self.providers,
            context_budget=self._context_budget(),
            api_enabled=self.config.api_enabled,
            budget_limit=self.config.budget_limit,
            evaluator=self._active_evaluator(),
            training_text=training_text,
            validation_text=validation_text,
            allow_training_upload=self.config.allow_training_upload,
        )

    def confirm_remote_preflight(self, text: str) -> str:
        preflight = self.preview_remote_calls(text)
        if preflight.budget_exceeded:
            raise ValueError("remote preflight budget exceeded")
        self._remote_confirmation_id = preflight.confirmation_id
        return preflight.confirmation_id

    def _consume_remote_confirmation(self, text: str) -> None:
        if not self.config.require_remote_confirmation:
            return
        preflight = self.preview_remote_calls(text)
        if not preflight.requires_confirmation:
            return
        if preflight.budget_exceeded:
            raise ValueError("remote preflight budget exceeded")
        if self._remote_confirmation_id != preflight.confirmation_id:
            raise PermissionError("remote preflight confirmation required")
        self._remote_confirmation_id = None

    def translate_text(self, text: str) -> ContextManagedTranslationResult:
        self._consume_remote_confirmation(text)
        training_text = self._load_optional_project_text(
            self.config.training_file,
            "training",
        )
        validation_text = self._load_optional_project_text(
            self.config.validation_file,
            "validation",
        )
        return run_context_managed_translation(
            text=text,
            source_lang=self.config.source_lang,
            target_lang=self.config.target_lang,
            topic=self.config.topic,
            mode=self.config.mode,
            providers=self.providers,
            context_budget=self._context_budget(),
            api_enabled=self.config.api_enabled,
            budget_limit=self.config.budget_limit,
            store=self.store,
            lexicon_store=self.lexicon_store,
            evaluator=self._active_evaluator(),
            training_text=training_text,
            validation_text=validation_text,
            allow_training_upload=self.config.allow_training_upload,
        )

    def translate_file(self, path: str | Path) -> ContextManagedTranslationResult:
        document = load_agent_input(path)
        result = self.translate_text(document.text)
        self.record_recent_file(path)
        return result

    def translate_files(self, paths: list[str | Path]) -> list[ContextManagedTranslationResult]:
        return [self.translate_file(path) for path in paths]

    def capture_plugin_input(self, plugin_id: str, **kwargs: object) -> CapturedInput:
        if plugin_id == "ocr-image":
            plugin = self.input_plugins.get(plugin_id)
            if isinstance(plugin, OcrImageInputPlugin):
                plugin.command = self._resolved_tesseract_command()
                plugin.default_lang = self.config.ocr_language.strip() or "jpn+eng"
        return self.input_plugins.capture(plugin_id, **kwargs)

    def translate_plugin_input(
        self,
        plugin_id: str,
        **kwargs: object,
    ) -> ContextManagedTranslationResult:
        capture = self.capture_plugin_input(plugin_id, **kwargs)
        return self.translate_text(capture.text)

    def capture_hook_text(self, process_ref: str, text: str) -> CapturedInput:
        plugin = self.input_plugins.get("hook-buffer")
        if not isinstance(plugin, HookTextBufferPlugin):
            appender = getattr(plugin, "append_text", None)
            if appender is None:
                raise ValueError("hook-buffer plugin does not support append_text")
            appender(process_ref, text)
        else:
            plugin.append_text(process_ref, text)
        return self.capture_plugin_input(
            "hook-buffer",
            process_ref=process_ref,
            consume=False,
        )

    def _config_to_profile(
        self,
        recent_files: list[str] | None = None,
    ) -> DesktopProjectProfile:
        return DesktopProjectProfile(
            project_id=self.project_id,
            source_lang=self.config.source_lang,
            target_lang=self.config.target_lang,
            topic=self.config.topic,
            mode=self.config.mode,
            max_context_tokens=self.config.max_context_tokens,
            reserved_output_tokens=self.config.reserved_output_tokens,
            api_enabled=self.config.api_enabled,
            budget_limit=self.config.budget_limit,
            require_remote_confirmation=self.config.require_remote_confirmation,
            allow_training_upload=self.config.allow_training_upload,
            training_file=self.config.training_file,
            validation_file=self.config.validation_file,
            evaluator_kind=self.config.evaluator_kind,
            tesseract_command=self.config.tesseract_command,
            ocr_language=self.config.ocr_language,
            comet_command=self.config.comet_command,
            comet_model=self.config.comet_model,
            comet_model_storage_path=self.config.comet_model_storage_path,
            recent_files=recent_files or [],
        )

    @staticmethod
    def _profile_to_config(profile: DesktopProjectProfile) -> DesktopAgentConfig:
        return DesktopAgentConfig(
            source_lang=profile.source_lang,
            target_lang=profile.target_lang,
            topic=profile.topic,
            mode=profile.mode,
            max_context_tokens=profile.max_context_tokens,
            reserved_output_tokens=profile.reserved_output_tokens,
            api_enabled=profile.api_enabled,
            budget_limit=profile.budget_limit,
            require_remote_confirmation=profile.require_remote_confirmation,
            allow_training_upload=profile.allow_training_upload,
            training_file=profile.training_file,
            validation_file=profile.validation_file,
            evaluator_kind=profile.evaluator_kind,
            tesseract_command=profile.tesseract_command,
            ocr_language=profile.ocr_language,
            comet_command=profile.comet_command,
            comet_model=profile.comet_model,
            comet_model_storage_path=profile.comet_model_storage_path,
        )

    def load_project_profile(self) -> DesktopProjectProfile | None:
        if self.store is None:
            return None
        getter = getattr(self.store, "get_project_profile", None)
        if getter is None:
            return None
        profile = getter(self.project_id)
        if profile is not None:
            self.config = self._profile_to_config(profile)
        return profile

    def save_project_profile(
        self,
        recent_files: list[str] | None = None,
    ) -> DesktopProjectProfile:
        existing_recent_files: list[str] = []
        if recent_files is None and self.store is not None:
            getter = getattr(self.store, "get_project_profile", None)
            if getter is not None:
                existing = getter(self.project_id)
                if existing is not None:
                    existing_recent_files = existing.recent_files
        profile = self._config_to_profile(
            recent_files=recent_files if recent_files is not None else existing_recent_files
        )
        if self.store is not None:
            saver = getattr(self.store, "save_project_profile", None)
            if saver is not None:
                saver(profile)
        return profile

    def record_recent_file(self, path: str | Path) -> DesktopProjectProfile:
        path_text = str(path)
        existing_files: list[str] = []
        if self.store is not None:
            getter = getattr(self.store, "get_project_profile", None)
            if getter is not None:
                existing = getter(self.project_id)
                if existing is not None:
                    existing_files = existing.recent_files
        recent_files = [path_text, *[item for item in existing_files if item != path_text]][:10]
        return self.save_project_profile(recent_files=recent_files)

    def load_enabled_provider_configs(self, credential_store: object) -> list[ModelProvider]:
        if self.store is None:
            return []
        lister = getattr(self.store, "list_provider_configs", None)
        if lister is None:
            return []
        providers = build_enabled_providers(
            list(lister(enabled=True)),
            credential_store,
        )
        self.providers = providers
        return providers

    def smoke_test_providers(
        self,
        sample_text: str = "hello",
    ) -> list[ProviderSmokeResult]:
        normalized_sample = sample_text.strip() or "hello"
        return [
            smoke_test_provider(
                provider,
                source_lang=self.config.source_lang,
                target_lang=self.config.target_lang,
                topic=self.config.topic,
                sample_text=normalized_sample,
                api_enabled=self.config.api_enabled,
            )
            for provider in self.providers
        ]

    def run_diagnostics(
        self,
        project_root: str | Path | None = None,
        credential_store: object | None = None,
        command_runner: CommandRunner | None = None,
        import_checker: ImportChecker | None = None,
        mode: str = "developer",
    ) -> DiagnosticReport:
        root = project_root or Path(__file__).resolve().parents[2]
        required_languages = tuple(
            language.strip()
            for language in self.config.ocr_language.split("+")
            if language.strip()
        )
        if mode == "installed":
            tesseract_command = (
                self.config.tesseract_command.strip()
                or str(self.runtime_layout.tesseract_command)
            )
            comet_command = (
                self.config.comet_command.strip()
                or str(self.runtime_layout.comet_command)
            )
        else:
            tesseract_command = self._resolved_tesseract_command()
            comet_command = self._resolved_comet_command()
        kwargs: dict[str, object] = {
            "project_root": root,
            "store": self.store,
            "credential_store": credential_store,
            "tesseract_command": tesseract_command,
            "comet_command": comet_command,
            "mode": mode,
            "required_ocr_languages": required_languages,
        }
        if command_runner is not None:
            kwargs["command_runner"] = command_runner
        if import_checker is not None:
            kwargs["import_checker"] = import_checker
        return run_desktop_diagnostics(**kwargs)

    def run_local_acceptance(
        self,
        output_dir: str | Path | None = None,
    ) -> LocalAcceptanceResult:
        acceptance_dir = (
            Path(output_dir)
            if output_dir is not None
            else default_desktop_store_path().parent / "acceptance"
        )
        return run_local_acceptance(
            acceptance_dir,
            project_id=f"{self.project_id}-acceptance",
        )

    def save_provider_settings(
        self,
        credential_store: LocalCredentialStore,
        provider_id: str,
        base_url: str,
        model: str,
        api_key: str,
        estimated_cost: float = 0.0,
        enabled: bool = True,
    ) -> ProviderConfig:
        if self.store is None:
            raise ValueError("provider settings require an AgentRunStore")
        normalized_provider_id = provider_id.strip()
        if not normalized_provider_id:
            raise ValueError("provider_id is required")
        if not base_url.strip():
            raise ValueError("base_url is required")
        if not model.strip():
            raise ValueError("model is required")

        credential_id = f"{normalized_provider_id}-key"
        if api_key:
            credential_store.set_secret(credential_id, api_key)
        config = ProviderConfig(
            provider_id=normalized_provider_id,
            kind="openai_compatible",
            base_url=base_url.strip(),
            model=model.strip(),
            credential_id=credential_id,
            estimated_cost=estimated_cost,
            enabled=enabled,
        )
        saver = getattr(self.store, "upsert_provider_config", None)
        if saver is None:
            raise ValueError("provider config store does not support upsert")
        saver(config)
        return config

    def list_audit_runs(self) -> list[dict[str, object]]:
        if self.store is None:
            return []
        lister = getattr(self.store, "list_agent_runs", None)
        if lister is None:
            return []
        return list(lister())

    def get_audit_run(self, run_id: str) -> dict[str, object] | None:
        if self.store is None:
            return None
        getter = getattr(self.store, "get_agent_run", None)
        if getter is None:
            return None
        return getter(run_id)

    def confirm_run(self, run_id: str) -> bool:
        if self.store is None:
            return False
        confirmer = getattr(self.store, "confirm_agent_run", None)
        if confirmer is None:
            return False
        return bool(confirmer(run_id))

    def list_pending_lexicon_updates(
        self,
        run_id: str | None = None,
    ) -> list[dict[str, object]]:
        active_store = self.lexicon_store or self.store
        if active_store is None:
            return []
        lister = getattr(active_store, "list_revision_events", None)
        if lister is None:
            return []
        return list(lister(confirmed=False, run_id=run_id))

    def confirm_lexicon_update(self, event_id: int) -> bool:
        active_store = self.lexicon_store or self.store
        if active_store is None:
            return False
        confirmer = getattr(active_store, "confirm_revision_event_by_id", None)
        if confirmer is None:
            return False
        return bool(confirmer(event_id))

    def export_topic_lexicon(self, topic: str | None = None) -> dict[str, dict[str, str]]:
        active_store = self.lexicon_store or self.store
        if active_store is None:
            return {"terms": {}, "phrases": {}, "style_rules": {}}
        exporter = getattr(active_store, "export_topic", None)
        if exporter is None:
            return {"terms": {}, "phrases": {}, "style_rules": {}}
        return exporter(topic or self.config.topic)

    def export_translation_artifacts(
        self,
        result: ContextManagedTranslationResult,
        output_dir: str | Path,
        base_name: str | None = None,
    ) -> dict[str, Path]:
        return export_translation_artifacts(
            result=result,
            output_dir=output_dir,
            base_name=base_name or self.project_id,
            project_id=self.project_id,
            config={
                "source_lang": self.config.source_lang,
                "target_lang": self.config.target_lang,
                "topic": self.config.topic,
                "mode": self.config.mode,
                "max_context_tokens": self.config.max_context_tokens,
                "reserved_output_tokens": self.config.reserved_output_tokens,
                "api_enabled": self.config.api_enabled,
                "budget_limit": self.config.budget_limit,
            },
        )


def default_desktop_store_path() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "ConsensusTranslation" / "agent.sqlite3"
    return Path.home() / ".consensus_translation" / "agent.sqlite3"


def default_desktop_credentials_path() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "ConsensusTranslation" / "credentials.json"
    return Path.home() / ".consensus_translation" / "credentials.json"


def format_remote_preflight_lines(preflight: RemoteCallPreflight) -> list[str]:
    if not preflight.calls:
        return ["remote calls: 0 | estimated cost: 0.0"]
    lines = [
        (
            f"remote calls: {len(preflight.calls)} | "
            f"estimated cost: {preflight.total_estimated_cost} | "
            f"budget: {preflight.budget_limit}"
        )
    ]
    lines.extend(
        (
            f"{call.provider_id} | {call.input_ref} | round={call.round_index} | "
            f"tokens={call.estimated_input_tokens} | cost={call.estimated_cost} | "
            f"scopes={','.join(call.data_scopes)}"
        )
        for call in preflight.calls
    )
    lines.extend(preflight.warnings)
    return lines


def _create_legacy_desktop_app(config: DesktopAgentConfig | None = None):
    import tkinter as tk
    from tkinter import ttk

    active_config = config or DesktopAgentConfig()
    controller = DesktopAgentController(active_config)
    root = tk.Tk()
    root.title("共识翻译 Agent")
    root.geometry("960x640")

    toolbar = ttk.Frame(root, padding=8)
    toolbar.pack(fill=tk.X)
    ttk.Label(toolbar, text="源语言").pack(side=tk.LEFT)
    ttk.Label(toolbar, text=active_config.source_lang, width=8).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="目标语言").pack(side=tk.LEFT)
    ttk.Label(toolbar, text=active_config.target_lang, width=8).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="模式").pack(side=tk.LEFT)
    ttk.Label(toolbar, text=active_config.mode, width=14).pack(side=tk.LEFT)

    pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    source = tk.Text(pane, wrap=tk.WORD)
    result = tk.Text(pane, wrap=tk.WORD)
    pane.add(source, weight=1)
    pane.add(result, weight=1)

    def run_translation() -> None:
        output = controller.translate_text(source.get("1.0", tk.END).strip())
        result.delete("1.0", tk.END)
        result.insert(tk.END, output.final_text)

    action_bar = ttk.Frame(root, padding=8)
    action_bar.pack(fill=tk.X)
    ttk.Button(action_bar, text="运行 Agent 翻译", command=run_translation).pack(side=tk.LEFT)
    return root


def create_desktop_app(
    config: DesktopAgentConfig | None = None,
    providers: list[ModelProvider] | None = None,
    evaluator: TranslationEvaluator | None = None,
    store: object | None = None,
    project_id: str = "default",
    credential_store: object | None = None,
):
    import tkinter as tk
    from tkinter import filedialog, ttk

    active_config = config or DesktopAgentConfig()
    credential_store = credential_store or LocalCredentialStore(
        default_desktop_credentials_path()
    )
    controller = DesktopAgentController(
        active_config,
        providers=providers,
        evaluator=evaluator,
        store=store,
        project_id=project_id,
    )
    loaded_profile = controller.load_project_profile()
    if loaded_profile is not None:
        active_config = controller.config
    root = tk.Tk()
    root.title("Consensus Translation Agent")
    root.geometry("1120x760")

    toolbar = ttk.Frame(root, padding=8)
    toolbar.pack(fill=tk.X)
    source_lang = tk.StringVar(value=active_config.source_lang)
    target_lang = tk.StringVar(value=active_config.target_lang)
    topic = tk.StringVar(value=active_config.topic)
    mode = tk.StringVar(value=active_config.mode)
    max_context_tokens = tk.StringVar(value=str(active_config.max_context_tokens))
    reserved_output_tokens = tk.StringVar(value=str(active_config.reserved_output_tokens))
    budget_limit = tk.StringVar(value=str(active_config.budget_limit))
    api_enabled = tk.BooleanVar(value=active_config.api_enabled)
    require_remote_confirmation = tk.BooleanVar(
        value=active_config.require_remote_confirmation
    )
    allow_training_upload = tk.BooleanVar(
        value=active_config.allow_training_upload
    )
    provider_id = tk.StringVar(value="remote-main")
    provider_base_url = tk.StringVar(value="https://api.example.test/v1")
    provider_model = tk.StringVar(value="translator")
    provider_api_key = tk.StringVar(value="")
    provider_estimated_cost = tk.StringVar(value="0.0")
    provider_enabled = tk.BooleanVar(value=True)
    training_file = tk.StringVar(value=active_config.training_file)
    validation_file = tk.StringVar(value=active_config.validation_file)
    evaluator_kind = tk.StringVar(value=active_config.evaluator_kind)
    tesseract_command = tk.StringVar(
        value=(
            active_config.tesseract_command
            or resolve_tesseract_command(project_root=controller._project_root())
        )
    )
    ocr_language = tk.StringVar(value=active_config.ocr_language)
    comet_command = tk.StringVar(
        value=(
            active_config.comet_command
            or resolve_comet_command(project_root=controller._project_root())
        )
    )
    comet_model = tk.StringVar(value=active_config.comet_model)
    comet_model_storage_path = tk.StringVar(
        value=(
            active_config.comet_model_storage_path
            or controller._resolved_comet_model_storage_path()
        )
    )

    def choose_document(variable: object, title: str) -> None:
        selected = filedialog.askopenfilename(
            title=title,
            filetypes=[
                ("Text documents", "*.txt *.md *.docx"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            variable.set(selected)

    def choose_executable(variable: object, title: str) -> None:
        selected = filedialog.askopenfilename(
            title=title,
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if selected:
            variable.set(selected)

    def choose_directory(variable: object, title: str) -> None:
        selected = filedialog.askdirectory(title=title)
        if selected:
            variable.set(selected)

    ttk.Label(toolbar, text="Source").pack(side=tk.LEFT)
    ttk.Entry(toolbar, textvariable=source_lang, width=6).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="Target").pack(side=tk.LEFT)
    ttk.Entry(toolbar, textvariable=target_lang, width=6).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="Topic").pack(side=tk.LEFT)
    ttk.Entry(toolbar, textvariable=topic, width=14).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="Mode").pack(side=tk.LEFT)
    ttk.Combobox(
        toolbar,
        textvariable=mode,
        values=("learning", "self_iterative", "self_decision"),
        state="readonly",
        width=14,
    ).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="Context").pack(side=tk.LEFT)
    ttk.Entry(toolbar, textvariable=max_context_tokens, width=7).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="Reserve").pack(side=tk.LEFT)
    ttk.Entry(toolbar, textvariable=reserved_output_tokens, width=6).pack(side=tk.LEFT)
    ttk.Label(toolbar, text="Budget").pack(side=tk.LEFT)
    ttk.Entry(toolbar, textvariable=budget_limit, width=6).pack(side=tk.LEFT)
    ttk.Checkbutton(toolbar, text="API", variable=api_enabled).pack(side=tk.LEFT)
    ttk.Checkbutton(
        toolbar,
        text="Confirm Remote",
        variable=require_remote_confirmation,
    ).pack(side=tk.LEFT)

    data_bar = ttk.Frame(root, padding=(8, 2))
    data_bar.pack(fill=tk.X)
    ttk.Label(data_bar, text="Training Set").grid(row=0, column=0, sticky="w")
    ttk.Entry(data_bar, textvariable=training_file).grid(
        row=0,
        column=1,
        sticky="ew",
        padx=(4, 4),
    )
    ttk.Button(
        data_bar,
        text="Browse",
        command=lambda: choose_document(training_file, "Select training set"),
    ).grid(row=0, column=2, padx=(0, 10))
    ttk.Label(data_bar, text="Validation Set").grid(row=0, column=3, sticky="w")
    ttk.Entry(data_bar, textvariable=validation_file).grid(
        row=0,
        column=4,
        sticky="ew",
        padx=(4, 4),
    )
    ttk.Button(
        data_bar,
        text="Browse",
        command=lambda: choose_document(validation_file, "Select validation set"),
    ).grid(row=0, column=5, padx=(0, 10))
    ttk.Label(data_bar, text="Evaluator").grid(row=0, column=6, sticky="w")
    ttk.Combobox(
        data_bar,
        textvariable=evaluator_kind,
        values=("deterministic", "comet"),
        state="readonly",
        width=14,
    ).grid(row=0, column=7, sticky="ew", padx=(4, 0))
    ttk.Checkbutton(
        data_bar,
        text="Upload Training",
        variable=allow_training_upload,
    ).grid(row=0, column=8, sticky="w", padx=(10, 0))
    data_bar.columnconfigure(1, weight=1)
    data_bar.columnconfigure(4, weight=1)

    runtime_bar = ttk.Frame(root, padding=(8, 2))
    runtime_bar.pack(fill=tk.X)
    ttk.Label(runtime_bar, text="OCR Lang").grid(row=0, column=0, sticky="w")
    ttk.Entry(runtime_bar, textvariable=ocr_language, width=12).grid(
        row=0,
        column=1,
        sticky="w",
        padx=(4, 10),
    )
    ttk.Label(runtime_bar, text="Tesseract").grid(row=0, column=2, sticky="w")
    ttk.Entry(runtime_bar, textvariable=tesseract_command).grid(
        row=0,
        column=3,
        sticky="ew",
        padx=(4, 4),
    )
    ttk.Button(
        runtime_bar,
        text="Browse",
        command=lambda: choose_executable(
            tesseract_command,
            "Select tesseract executable",
        ),
    ).grid(row=0, column=4)
    ttk.Label(runtime_bar, text="COMET Command").grid(
        row=1,
        column=0,
        sticky="w",
        pady=(4, 0),
    )
    ttk.Entry(runtime_bar, textvariable=comet_command).grid(
        row=1,
        column=1,
        columnspan=3,
        sticky="ew",
        padx=(4, 4),
        pady=(4, 0),
    )
    ttk.Button(
        runtime_bar,
        text="Browse",
        command=lambda: choose_executable(comet_command, "Select comet-score"),
    ).grid(row=1, column=4, pady=(4, 0))
    ttk.Label(runtime_bar, text="COMET Model").grid(
        row=2,
        column=0,
        sticky="w",
        pady=(4, 0),
    )
    ttk.Entry(runtime_bar, textvariable=comet_model).grid(
        row=2,
        column=1,
        sticky="ew",
        padx=(4, 10),
        pady=(4, 0),
    )
    ttk.Label(runtime_bar, text="COMET Cache").grid(
        row=2,
        column=2,
        sticky="w",
        pady=(4, 0),
    )
    ttk.Entry(runtime_bar, textvariable=comet_model_storage_path).grid(
        row=2,
        column=3,
        sticky="ew",
        padx=(4, 4),
        pady=(4, 0),
    )
    ttk.Button(
        runtime_bar,
        text="Browse",
        command=lambda: choose_directory(comet_model_storage_path, "Select COMET cache"),
    ).grid(row=2, column=4, pady=(4, 0))
    runtime_bar.columnconfigure(1, weight=1)
    runtime_bar.columnconfigure(3, weight=2)

    provider_bar = ttk.Frame(root, padding=8)
    provider_bar.pack(fill=tk.X)
    ttk.Label(provider_bar, text="Provider ID").pack(side=tk.LEFT)
    ttk.Entry(provider_bar, textvariable=provider_id, width=14).pack(side=tk.LEFT)
    ttk.Label(provider_bar, text="Base URL").pack(side=tk.LEFT)
    ttk.Entry(provider_bar, textvariable=provider_base_url, width=28).pack(side=tk.LEFT)
    ttk.Label(provider_bar, text="Model").pack(side=tk.LEFT)
    ttk.Entry(provider_bar, textvariable=provider_model, width=18).pack(side=tk.LEFT)
    ttk.Label(provider_bar, text="API Key").pack(side=tk.LEFT)
    ttk.Entry(
        provider_bar,
        textvariable=provider_api_key,
        width=18,
        show="*",
    ).pack(side=tk.LEFT)
    ttk.Label(provider_bar, text="Cost").pack(side=tk.LEFT)
    ttk.Entry(provider_bar, textvariable=provider_estimated_cost, width=6).pack(
        side=tk.LEFT
    )
    ttk.Checkbutton(provider_bar, text="Enabled", variable=provider_enabled).pack(
        side=tk.LEFT
    )

    pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    pane.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    source = tk.Text(pane, wrap=tk.WORD)
    result = tk.Text(pane, wrap=tk.WORD)
    pane.add(source, weight=1)
    pane.add(result, weight=1)

    review = ttk.Frame(root, padding=8)
    review.pack(fill=tk.BOTH)
    candidates = tk.Listbox(review, height=4)
    audit = tk.Listbox(review, height=4)
    pending = tk.Listbox(review, height=4)
    preflight = tk.Listbox(review, height=4)
    recent = tk.Listbox(review, height=4)
    candidates.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    audit.grid(row=0, column=1, sticky="nsew", padx=6)
    pending.grid(row=0, column=2, sticky="nsew", padx=6)
    preflight.grid(row=0, column=3, sticky="nsew", padx=6)
    recent.grid(row=0, column=4, sticky="nsew", padx=(6, 0))
    for column in range(5):
        review.columnconfigure(column, weight=1)

    last_run_id = tk.StringVar(value="")
    last_output: dict[str, ContextManagedTranslationResult | None] = {"result": None}

    def sync_config_from_ui() -> None:
        controller.config = DesktopAgentConfig(
            source_lang=source_lang.get().strip() or "zh",
            target_lang=target_lang.get().strip() or "ja",
            topic=topic.get().strip() or "general",
            mode=mode.get().strip() or "learning",
            max_context_tokens=int(max_context_tokens.get() or "4096"),
            reserved_output_tokens=int(reserved_output_tokens.get() or "1024"),
            api_enabled=bool(api_enabled.get()),
            budget_limit=float(budget_limit.get() or "0"),
            require_remote_confirmation=bool(require_remote_confirmation.get()),
            allow_training_upload=bool(allow_training_upload.get()),
            training_file=training_file.get().strip(),
            validation_file=validation_file.get().strip(),
            evaluator_kind=evaluator_kind.get().strip() or "deterministic",
            tesseract_command=tesseract_command.get().strip(),
            ocr_language=ocr_language.get().strip() or "jpn+eng",
            comet_command=comet_command.get().strip(),
            comet_model=comet_model.get().strip() or "Unbabel/wmt22-comet-da",
            comet_model_storage_path=comet_model_storage_path.get().strip(),
        )

    def refresh_project_data() -> None:
        recent.delete(0, tk.END)
        if controller.store is None:
            return
        getter = getattr(controller.store, "get_project_profile", None)
        if getter is None:
            return
        profile = getter(controller.project_id)
        if profile is None:
            return
        for path in profile.recent_files:
            recent.insert(tk.END, path)

    def refresh_review_data() -> None:
        audit.delete(0, tk.END)
        for row in controller.list_audit_runs():
            audit.insert(
                tk.END,
                f"{row['run_id']} | {row['status']} | score={row['final_score']}",
            )
        pending.delete(0, tk.END)
        for row in controller.list_pending_lexicon_updates():
            pending.insert(
                tk.END,
                f"#{row['id']} | {row['layer']} | {row['source']} -> {row['target']}",
            )
        refresh_project_data()

    def save_project() -> None:
        sync_config_from_ui()
        controller.save_project_profile()
        refresh_project_data()

    def open_files() -> None:
        paths = filedialog.askopenfilenames(
            title="Open source files",
            filetypes=[
                ("Text documents", "*.txt *.md *.docx"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        for path in paths:
            controller.record_recent_file(path)
        document = load_agent_input(paths[0])
        source.delete("1.0", tk.END)
        source.insert(tk.END, document.text)
        refresh_project_data()

    def open_ocr_image() -> None:
        path = filedialog.askopenfilename(
            title="Open OCR image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        preflight.delete(0, tk.END)
        try:
            capture = controller.capture_plugin_input("ocr-image", path=path)
        except (RuntimeError, ValueError) as exc:
            preflight.insert(tk.END, str(exc))
            return
        source.delete("1.0", tk.END)
        source.insert(tk.END, capture.text)
        controller.record_recent_file(path)
        for warning in capture.warnings:
            preflight.insert(tk.END, warning)
        refresh_project_data()

    def import_hook_text() -> None:
        preflight.delete(0, tk.END)
        try:
            clipboard_text = root.clipboard_get()
        except tk.TclError as exc:
            preflight.insert(tk.END, f"clipboard unavailable: {exc}")
            return
        capture = controller.capture_hook_text("clipboard", clipboard_text)
        source.delete("1.0", tk.END)
        source.insert(tk.END, capture.text)
        controller.capture_plugin_input("hook-buffer", process_ref="clipboard")
        for warning in capture.warnings:
            preflight.insert(tk.END, warning)

    def render_remote_preflight(prefix: str | None = None) -> None:
        sync_config_from_ui()
        preflight.delete(0, tk.END)
        if prefix:
            preflight.insert(tk.END, prefix)
        try:
            preview = controller.preview_remote_calls(
                source.get("1.0", tk.END).strip()
            )
        except ValueError as exc:
            preflight.insert(tk.END, str(exc))
            return
        for line in format_remote_preflight_lines(preview):
            preflight.insert(tk.END, line)

    def preview_remote_calls() -> None:
        render_remote_preflight()

    def confirm_remote_calls() -> None:
        sync_config_from_ui()
        text = source.get("1.0", tk.END).strip()
        try:
            confirmation_id = controller.confirm_remote_preflight(text)
        except ValueError as exc:
            render_remote_preflight(prefix=str(exc))
            return
        render_remote_preflight(prefix=f"confirmed: {confirmation_id}")

    def run_translation() -> None:
        sync_config_from_ui()
        try:
            output = controller.translate_text(source.get("1.0", tk.END).strip())
        except (OSError, PermissionError, RuntimeError, ValueError) as exc:
            result.delete("1.0", tk.END)
            result.insert(tk.END, str(exc))
            render_remote_preflight()
            return
        result.delete("1.0", tk.END)
        result.insert(tk.END, output.final_text)
        last_output["result"] = output
        candidates.delete(0, tk.END)
        if output.initial_task.run is not None:
            last_run_id.set(output.initial_task.run.contract.run_id)
            for candidate in output.initial_task.run.candidates:
                candidates.insert(
                    tk.END,
                    f"{candidate.provider_id} | confidence={candidate.confidence} | {candidate.text[:80]}",
                )
        refresh_review_data()

    def confirm_current_run() -> None:
        if last_run_id.get():
            controller.confirm_run(last_run_id.get())
            refresh_review_data()

    def confirm_selected_lexicon_update() -> None:
        selection = pending.curselection()
        if not selection:
            return
        selected = pending.get(selection[0])
        event_id = int(selected.split("|", 1)[0].strip().lstrip("#"))
        controller.confirm_lexicon_update(event_id)
        refresh_review_data()

    def save_provider_settings() -> None:
        preflight.delete(0, tk.END)
        try:
            config = controller.save_provider_settings(
                credential_store=credential_store,
                provider_id=provider_id.get(),
                base_url=provider_base_url.get(),
                model=provider_model.get(),
                api_key=provider_api_key.get(),
                estimated_cost=float(provider_estimated_cost.get() or "0"),
                enabled=bool(provider_enabled.get()),
            )
        except ValueError as exc:
            preflight.insert(tk.END, str(exc))
            return
        preflight.insert(tk.END, f"saved provider: {config.provider_id}")

    def load_provider_settings() -> None:
        preflight.delete(0, tk.END)
        try:
            providers = controller.load_enabled_provider_configs(credential_store)
        except KeyError as exc:
            preflight.insert(tk.END, str(exc))
            return
        preflight.insert(tk.END, f"loaded providers: {len(providers)}")
        for provider in providers:
            preflight.insert(tk.END, provider.provider_id)

    def smoke_provider_settings() -> None:
        sync_config_from_ui()
        preflight.delete(0, tk.END)
        sample_text = source.get("1.0", tk.END).strip() or "hello"
        results = controller.smoke_test_providers(sample_text=sample_text[:200])
        for line in format_provider_smoke_lines(results):
            preflight.insert(tk.END, line)

    def run_diagnostics() -> None:
        sync_config_from_ui()
        preflight.delete(0, tk.END)
        report = controller.run_diagnostics(credential_store=credential_store)
        for line in format_diagnostic_lines(report):
            preflight.insert(tk.END, line)

    def run_local_smoke() -> None:
        sync_config_from_ui()
        preflight.delete(0, tk.END)
        smoke = controller.run_local_acceptance()
        for line in format_acceptance_lines(smoke):
            preflight.insert(tk.END, line)

    def export_current_artifacts() -> None:
        output = last_output["result"]
        preflight.delete(0, tk.END)
        if output is None:
            preflight.insert(tk.END, "no translation result to export")
            return
        directory = filedialog.askdirectory(title="Export translation artifacts")
        if not directory:
            return
        artifacts = controller.export_translation_artifacts(
            output,
            output_dir=directory,
            base_name=controller.project_id,
        )
        for name, path in artifacts.items():
            preflight.insert(tk.END, f"exported {name}: {path}")

    action_bar = ttk.Frame(root, padding=8)
    action_bar.pack(fill=tk.X)
    ttk.Button(action_bar, text="Open Files", command=open_files).pack(side=tk.LEFT)
    ttk.Button(action_bar, text="Open OCR Image", command=open_ocr_image).pack(
        side=tk.LEFT,
        padx=6,
    )
    ttk.Button(action_bar, text="Import Hook Text", command=import_hook_text).pack(
        side=tk.LEFT,
    )
    ttk.Button(action_bar, text="Save Project", command=save_project).pack(
        side=tk.LEFT,
        padx=6,
    )
    ttk.Button(
        action_bar,
        text="Preview Remote Calls",
        command=preview_remote_calls,
    ).pack(side=tk.LEFT)
    ttk.Button(
        action_bar,
        text="Save Provider",
        command=save_provider_settings,
    ).pack(side=tk.LEFT, padx=6)
    ttk.Button(
        action_bar,
        text="Load Providers",
        command=load_provider_settings,
    ).pack(side=tk.LEFT)
    ttk.Button(
        action_bar,
        text="Smoke Providers",
        command=smoke_provider_settings,
    ).pack(side=tk.LEFT, padx=6)
    ttk.Button(
        action_bar,
        text="Run Diagnostics",
        command=run_diagnostics,
    ).pack(side=tk.LEFT)
    ttk.Button(
        action_bar,
        text="Run Local Smoke",
        command=run_local_smoke,
    ).pack(side=tk.LEFT, padx=6)
    ttk.Button(
        action_bar,
        text="Confirm Remote Calls",
        command=confirm_remote_calls,
    ).pack(side=tk.LEFT, padx=6)
    ttk.Button(action_bar, text="Run Agent", command=run_translation).pack(side=tk.LEFT)
    ttk.Button(action_bar, text="Confirm Run", command=confirm_current_run).pack(
        side=tk.LEFT,
        padx=6,
    )
    ttk.Button(
        action_bar,
        text="Confirm Lexicon Update",
        command=confirm_selected_lexicon_update,
    ).pack(side=tk.LEFT)
    ttk.Button(
        action_bar,
        text="Export Artifacts",
        command=export_current_artifacts,
    ).pack(side=tk.LEFT, padx=6)
    refresh_review_data()
    return root


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--local-smoke", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--acceptance-dir")
    parser.add_argument("--report-json")
    parser.add_argument("--project-root")
    parser.add_argument("--install-root")
    parser.add_argument("--data-dir")
    parser.add_argument(
        "--diagnostics-mode",
        choices=("developer", "installed"),
    )
    parser.add_argument("--project-id", default="default")
    args = parser.parse_args(argv)

    explicit_data_dir = Path(args.data_dir) if args.data_dir else None

    if args.local_smoke:
        controller = DesktopAgentController(project_id=args.project_id)
        result = controller.run_local_acceptance(args.acceptance_dir)
        for line in format_acceptance_lines(result):
            print(line)
        if args.report_json:
            write_acceptance_report(result, args.report_json)
        elif args.acceptance_dir:
            report_path = Path(args.acceptance_dir) / "local-smoke-report.json"
            write_acceptance_report(result, report_path)
        else:
            _ = acceptance_report_payload(result)
        return 0 if result.ok else 2

    if args.diagnostics:
        diagnostic_root = args.install_root or args.project_root or Path.cwd()
        diagnostic_mode = args.diagnostics_mode or (
            "installed" if getattr(sys, "frozen", False) else "developer"
        )
        runtime_layout = RuntimeLayout.discover(
            project_root=args.project_root or diagnostic_root,
            install_root=args.install_root,
            data_root=explicit_data_dir,
        )
        diagnostic_data_dir = explicit_data_dir or runtime_layout.data_root
        store = AgentRunStore(diagnostic_data_dir / "agent.sqlite3")
        credential_store = LocalCredentialStore(
            diagnostic_data_dir / "credentials.json"
        )
        controller = DesktopAgentController(
            store=store,
            project_id=args.project_id,
            runtime_layout=runtime_layout,
        )
        report = controller.run_diagnostics(
            project_root=diagnostic_root,
            credential_store=credential_store,
            mode=diagnostic_mode,
        )
        for line in format_diagnostic_lines(report):
            print(line)
        if args.report_json:
            write_diagnostic_report(report, args.report_json)
        else:
            _ = diagnostic_report_payload(report)
        return 2 if report.overall_status == "error" else 0

    if explicit_data_dir:
        store_path = explicit_data_dir / "agent.sqlite3"
        credentials_path = explicit_data_dir / "credentials.json"
    else:
        store_path = default_desktop_store_path()
        credentials_path = default_desktop_credentials_path()

    store = AgentRunStore(store_path)
    app = create_desktop_app(
        store=store,
        credential_store=LocalCredentialStore(credentials_path),
    )
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
