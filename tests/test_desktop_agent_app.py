from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_providers import EchoModelProvider
from consensus_translation.agent_providers import ProviderRequest
from consensus_translation.agent_providers import StaticModelProvider
from consensus_translation.agent_contracts import TranslationCandidate
from consensus_translation.agent_diagnostics import CommandResult
from consensus_translation.agent_evaluators import EvaluationResult
from consensus_translation.agent_input_plugins import (
    HookTextBufferPlugin,
    InputPluginRegistry,
    OcrImageInputPlugin,
)
from consensus_translation.agent_provider_config import ProviderConfig
from consensus_translation.agent_runtime import RuntimeLayout
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.desktop_agent_app import (
    DesktopAgentConfig,
    DesktopAgentController,
    default_desktop_store_path,
    format_remote_preflight_lines,
    main as desktop_main,
)


class RemoteEvaluator:
    evaluator_id = "llm-judge"
    requires_api = True
    estimated_cost = 0.1


class DesktopSmokeFailingProvider:
    provider_id = "remote-failing"
    requires_api = True
    estimated_cost = 0.5

    def translate(self, request: ProviderRequest) -> TranslationCandidate:
        raise RuntimeError("endpoint unavailable")


class FakeDesktopCredentialStore:
    def __init__(self, secrets):
        self._secrets = secrets

    def get_secret(self, credential_id):
        if credential_id not in self._secrets:
            raise KeyError(f"credential not found: {credential_id}")
        return self._secrets[credential_id]


class PassingDesktopEvaluator:
    evaluator_id = "passing"
    requires_api = False
    estimated_cost = 0.0

    def evaluate(self, request):
        return EvaluationResult(
            evaluator_id=self.evaluator_id,
            score=0.9,
            metrics={"score": 0.9},
        )


class CapturingTrainingProvider:
    provider_id = "capture-training"
    requires_api = False
    estimated_cost = 0.0

    def __init__(self):
        self.requests = []

    def translate(self, request):
        self.requests.append(request)
        return TranslationCandidate(
            provider_id=self.provider_id,
            text=f"ZH:{request.text}",
            confidence=0.9,
        )


def _ready_desktop_project_root(root: Path) -> Path:
    (root / "src" / "consensus_translation").mkdir(parents=True)
    (root / "src" / "consensus_translation" / "desktop_agent_app.py").write_text(
        "# desktop entrypoint",
        encoding="utf-8",
    )
    (root / "packaging").mkdir()
    (root / "packaging" / "desktop_agent.spec").write_text("# spec", encoding="utf-8")
    (root / "build_desktop_agent.ps1").write_text("# build", encoding="utf-8")
    (root / "requirements-desktop.txt").write_text("PyInstaller", encoding="utf-8")
    (root / "install_optional_runtimes.ps1").write_text(
        "# runtime installer",
        encoding="utf-8",
    )
    app_dir = root / "dist" / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"exe")
    (root / "README.md").write_text("# Readme", encoding="utf-8")
    return root


def test_desktop_agent_config_defaults_to_context_managed_local_mode():
    config = DesktopAgentConfig()

    assert config.source_lang == "zh"
    assert config.target_lang == "ja"
    assert config.mode == "learning"
    assert config.max_context_tokens > config.reserved_output_tokens
    assert config.api_enabled is False
    assert config.allow_training_upload is False


def test_default_desktop_store_path_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    path = default_desktop_store_path()

    assert path == tmp_path / "ConsensusTranslation" / "agent.sqlite3"


def test_desktop_agent_controller_runs_context_managed_translation():
    controller = DesktopAgentController(
        DesktopAgentConfig(
            max_context_tokens=18,
            reserved_output_tokens=5,
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("echo-local", prefix="JP:")],
    )

    result = controller.translate_text(
        "第一段命运之轮转动。\n\n第二段利维坦苏醒。"
    )

    assert result.final_text == "JP:第一段命运之轮转动。\n\nJP:第二段利维坦苏醒。"
    assert result.verification["order_preserved"] is True


def test_desktop_agent_controller_blocks_mock_provider_by_default():
    controller = DesktopAgentController(
        DesktopAgentConfig(max_context_tokens=18, reserved_output_tokens=5),
        providers=[EchoModelProvider("echo-local", prefix="JP:")],
    )

    try:
        controller.translate_text("hello")
    except PermissionError as exc:
        assert "mock providers are disabled" in str(exc)
    else:
        raise AssertionError("mock provider should be blocked by default")


def test_desktop_agent_controller_translates_file_and_persists_audit(tmp_path):
    source_file = tmp_path / "chapter.txt"
    source_file.write_text("第一段命运之轮转动。\n\n第二段利维坦苏醒。", encoding="utf-8")
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    controller = DesktopAgentController(
        DesktopAgentConfig(
            max_context_tokens=18,
            reserved_output_tokens=5,
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("echo-local", prefix="JP:")],
        store=store,
    )

    result = controller.translate_file(source_file)

    assert result.final_text == "JP:第一段命运之轮转动。\n\nJP:第二段利维坦苏醒。"
    assert result.initial_task.run is not None
    rows = store.list_agent_runs()
    assert rows
    assert rows[0]["final_text"].startswith("JP:")


def test_desktop_agent_controller_exposes_audit_and_confirmation_actions(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            topic="western_myth",
            max_context_tokens=64,
            reserved_output_tokens=8,
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("echo-local", prefix="ZH:")],
        store=store,
    )

    result = controller.translate_text("Leviathan")
    run_id = result.initial_task.run.contract.run_id
    pending = controller.list_pending_lexicon_updates()

    assert controller.list_audit_runs()[0]["run_id"] == run_id
    assert controller.get_audit_run(run_id)["status"] == "awaiting_human_confirmation"
    assert pending[0]["source"] == "Leviathan"
    assert controller.confirm_run(run_id) is True
    assert controller.get_audit_run(run_id)["status"] == "finalized"
    assert controller.confirm_lexicon_update(pending[0]["id"]) is True
    assert controller.export_topic_lexicon("western_myth")["terms"] == {
        "Leviathan": "ZH:Leviathan"
    }
    assert controller.list_pending_lexicon_updates() == []


def test_desktop_agent_controller_requires_remote_preflight_confirmation():
    remote = StaticModelProvider(
        "remote-a",
        "remote translation",
        confidence=0.9,
        estimated_cost=0.25,
        requires_api=True,
    )
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            api_enabled=True,
            budget_limit=1.0,
            max_context_tokens=64,
            reserved_output_tokens=8,
        ),
        providers=[remote],
    )

    preflight = controller.preview_remote_calls("Leviathan")

    assert preflight.requires_confirmation is True
    assert preflight.total_estimated_cost == 0.25
    try:
        controller.translate_text("Leviathan")
    except PermissionError as exc:
        assert "remote preflight confirmation required" in str(exc)
    else:
        raise AssertionError("remote call should require preflight confirmation")
    assert remote.calls == 0

    confirmation_id = controller.confirm_remote_preflight("Leviathan")
    result = controller.translate_text("Leviathan")

    assert confirmation_id == preflight.confirmation_id
    assert result.final_text == "remote translation"
    assert remote.calls == 1
    try:
        controller.translate_text("Leviathan")
    except PermissionError:
        pass
    else:
        raise AssertionError("remote preflight confirmation should be single-use")
    assert remote.calls == 1


def test_desktop_agent_formats_remote_preflight_for_review_panel():
    remote = StaticModelProvider(
        "remote-a",
        "remote translation",
        confidence=0.9,
        estimated_cost=0.25,
        requires_api=True,
    )
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            api_enabled=True,
            budget_limit=1.0,
            max_context_tokens=64,
            reserved_output_tokens=8,
        ),
        providers=[remote],
    )

    lines = format_remote_preflight_lines(controller.preview_remote_calls("Leviathan"))

    assert lines == [
        "remote calls: 1 | estimated cost: 0.25 | budget: 1.0",
        "remote-a | context-initial | round=1 | tokens=1 | cost=0.25 | scopes=source",
    ]


def test_desktop_agent_preflight_includes_remote_evaluator():
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            mode="self_iterative",
            api_enabled=True,
            budget_limit=1.0,
            max_context_tokens=64,
            reserved_output_tokens=8,
        ),
        providers=[StaticModelProvider("local-a", "local", confidence=0.6)],
        evaluator=RemoteEvaluator(),
    )

    lines = format_remote_preflight_lines(controller.preview_remote_calls("alpha beta"))

    assert lines == [
        "remote calls: 3 | estimated cost: 0.3 | budget: 1.0",
        "evaluator:llm-judge | context-initial | round=1 | tokens=4 | cost=0.1 | scopes=source,candidate",
        "evaluator:llm-judge | context-initial | round=2 | tokens=4 | cost=0.1 | scopes=source,candidate",
        "evaluator:llm-judge | context-initial | round=3 | tokens=4 | cost=0.1 | scopes=source,candidate",
        "validation_data_missing",
    ]


def test_desktop_agent_controller_translates_multiple_files_in_order(tmp_path):
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("第一段。", encoding="utf-8")
    second.write_text("第二段。", encoding="utf-8")
    controller = DesktopAgentController(
        DesktopAgentConfig(allow_mock_providers=True),
        providers=[EchoModelProvider("echo-local", prefix="JP:")]
    )

    results = controller.translate_files([first, second])

    assert [result.final_text for result in results] == ["JP:第一段。", "JP:第二段。"]

def test_desktop_agent_controller_captures_and_translates_ocr_input(tmp_path):
    image_path = tmp_path / "panel.png"
    image_path.write_bytes(b"fake image bytes")
    registry = InputPluginRegistry()
    registry.register(OcrImageInputPlugin(ocr_fn=lambda path, lang: "リヴァイアサン"))
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="ja",
            target_lang="zh",
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("echo-local", prefix="ZH:")],
        input_plugins=registry,
    )

    capture = controller.capture_plugin_input("ocr-image", path=image_path)
    result = controller.translate_plugin_input("ocr-image", path=image_path)

    assert capture.source_type == "ocr"
    assert capture.text == "リヴァイアサン"
    assert result.final_text == "ZH:リヴァイアサン"


def test_desktop_agent_controller_captures_hook_text_buffer():
    registry = InputPluginRegistry()
    registry.register(HookTextBufferPlugin())
    controller = DesktopAgentController(
        DesktopAgentConfig(allow_mock_providers=True),
        providers=[EchoModelProvider("echo-local", prefix="ZH:")],
        input_plugins=registry,
    )

    capture = controller.capture_hook_text("game.exe:1234", "第一行")
    result = controller.translate_plugin_input(
        "hook-buffer",
        process_ref="game.exe:1234",
    )

    assert capture.input_ref == "hook:game.exe:1234"
    assert capture.text == "第一行"
    assert result.final_text == "ZH:第一行"


def test_desktop_agent_controller_exports_translation_artifacts(tmp_path):
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            max_context_tokens=7,
            reserved_output_tokens=2,
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("echo-local", prefix="ZH:")],
    )
    result = controller.translate_text("alpha beta\n\ngamma delta\n\nomega zeta")

    artifacts = controller.export_translation_artifacts(
        result,
        output_dir=tmp_path,
        base_name="chapter01",
    )

    assert artifacts["final_text"].read_text(encoding="utf-8") == result.final_text
    manifest = json.loads(artifacts["manifest"].read_text(encoding="utf-8"))
    assert manifest["project_id"] == "default"
    assert manifest["verification"]["status"] == "passed"


def test_desktop_agent_controller_smoke_tests_current_providers():
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            topic="smoke",
            api_enabled=True,
        ),
        providers=[
            StaticModelProvider(
                "remote-a",
                "remote smoke translation",
                confidence=0.8,
                estimated_cost=0.25,
                requires_api=True,
            ),
            DesktopSmokeFailingProvider(),
        ],
    )

    results = controller.smoke_test_providers(
        sample_text="Leviathan",
        allow_live_remote=True,
    )

    assert [result.provider_id for result in results] == ["remote-a", "remote-failing"]
    assert results[0].ok is True
    assert results[0].translated_text == "remote smoke translation"
    assert results[1].ok is False
    assert results[1].error == "endpoint unavailable"


def test_desktop_agent_controller_smoke_respects_api_disabled():
    remote = StaticModelProvider(
        "remote-a",
        "remote smoke translation",
        confidence=0.8,
        estimated_cost=0.25,
        requires_api=True,
    )
    controller = DesktopAgentController(
        DesktopAgentConfig(source_lang="en", target_lang="zh", api_enabled=False),
        providers=[remote],
    )

    results = controller.smoke_test_providers(sample_text="Leviathan")

    assert results[0].ok is False
    assert results[0].error == "api disabled"
    assert remote.calls == 0


def test_desktop_agent_controller_smoke_blocks_live_remote_by_default():
    remote = StaticModelProvider(
        "remote-a",
        "remote smoke translation",
        confidence=0.8,
        estimated_cost=0.25,
        requires_api=True,
    )
    controller = DesktopAgentController(
        DesktopAgentConfig(source_lang="en", target_lang="zh", api_enabled=True),
        providers=[remote],
    )

    results = controller.smoke_test_providers(sample_text="Leviathan")

    assert results[0].ok is False
    assert results[0].error == "live remote smoke requires explicit confirmation"
    assert remote.calls == 0


def test_desktop_agent_controller_runs_delivery_diagnostics(tmp_path):
    project_root = _ready_desktop_project_root(tmp_path / "project")
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    store.upsert_provider_config(
        ProviderConfig(
            provider_id="remote-a",
            kind="openai_compatible",
            base_url="https://api.example.test/v1",
            model="translator",
            credential_id="remote-a-key",
            estimated_cost=0.25,
            enabled=True,
        )
    )
    controller = DesktopAgentController(store=store)

    report = controller.run_diagnostics(
        project_root=project_root,
        credential_store=FakeDesktopCredentialStore({"remote-a-key": "sk-test"}),
        command_runner=lambda command: CommandResult(0, "tesseract 5.0", ""),
        import_checker=lambda name: object(),
    )

    statuses = {check.check_id: check.status for check in report.checks}
    assert statuses["desktop_packaging"] == "ok"
    assert statuses["desktop_release"] == "ok"
    assert statuses["provider_configs"] == "ok"
    assert statuses["gui_smoke"] == "warning"


def test_desktop_controller_uses_configured_runtime_commands_for_diagnostics(tmp_path):
    project_root = _ready_desktop_project_root(tmp_path / "project")
    captured_commands = []

    def command_runner(command):
        captured_commands.append(command)
        if command[-1] == "--list-langs":
            return CommandResult(0, "eng\njpn", "")
        return CommandResult(0, "runtime ok", "")

    controller = DesktopAgentController(
        DesktopAgentConfig(
            tesseract_command=r"E:\runtime\Tesseract-OCR\tesseract.exe",
            comet_command=r"E:\runtime\comet-score.cmd",
        )
    )

    report = controller.run_diagnostics(
        project_root=project_root,
        command_runner=command_runner,
        import_checker=lambda name: object() if name == "PyInstaller" else None,
    )

    statuses = {check.check_id: check.status for check in report.checks}
    assert captured_commands[:3] == [
        [r"E:\runtime\Tesseract-OCR\tesseract.exe", "--version"],
        [r"E:\runtime\Tesseract-OCR\tesseract.exe", "--list-langs"],
        [r"E:\runtime\comet-score.cmd", "--help"],
    ]
    assert statuses["ocr_tesseract"] == "ok"
    assert statuses["comet_runtime"] == "ok"


def test_installed_diagnostics_only_checks_selected_install_runtime(tmp_path):
    install_root = tmp_path / "installed"
    app_dir = install_root / "ConsensusTranslationAgent"
    app_dir.mkdir(parents=True)
    (app_dir / "ConsensusTranslationAgent.exe").write_bytes(b"exe")
    captured_commands = []

    def command_runner(command):
        captured_commands.append(command)
        return CommandResult(127, "", "not found")

    controller = DesktopAgentController(
        runtime_layout=RuntimeLayout.from_roots(install_root)
    )

    controller.run_diagnostics(
        project_root=install_root,
        command_runner=command_runner,
        import_checker=lambda name: None,
        mode="installed",
    )

    assert captured_commands[0] == [
        str(
            install_root
            / "runtime"
            / "Tesseract-OCR"
            / "tesseract.exe"
        ),
        "--version",
    ]
    assert captured_commands[1] == [
        str(
            install_root
            / "runtime"
            / "comet-score.cmd"
        ),
        "--help",
    ]


def test_desktop_controller_loads_training_and_validation_files(tmp_path):
    training = tmp_path / "training.txt"
    validation = tmp_path / "validation.txt"
    training.write_text("training example", encoding="utf-8")
    validation.write_text("reference translation", encoding="utf-8")
    provider = CapturingTrainingProvider()
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="zh",
            mode="self_iterative",
            max_context_tokens=64,
            reserved_output_tokens=8,
            training_file=str(training),
            validation_file=str(validation),
        ),
        providers=[provider],
        evaluator=PassingDesktopEvaluator(),
    )

    result = controller.translate_text("source paragraph")

    assert result.final_text == "ZH:source paragraph"
    assert provider.requests[0].training_text == "training example"


def test_desktop_agent_controller_runs_local_acceptance_smoke(tmp_path):
    controller = DesktopAgentController()

    result = controller.run_local_acceptance(tmp_path / "acceptance")

    assert result.ok is True
    assert result.verification["status"] == "passed"
    assert result.artifacts["manifest"].exists()


def test_desktop_agent_main_runs_local_smoke_without_opening_gui(tmp_path):
    report_path = tmp_path / "desktop-smoke-report.json"
    artifact_dir = tmp_path / "desktop-smoke"

    exit_code = desktop_main(
        [
            "--local-smoke",
            "--acceptance-dir",
            str(artifact_dir),
            "--report-json",
            str(report_path),
            "--project-id",
            "desktop-cli",
        ]
    )

    assert exit_code == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["verification"]["status"] == "passed"
    assert "continuation_translation" in payload["task_types"]


def test_desktop_agent_main_runs_diagnostics_without_opening_gui(tmp_path):
    project_root = _ready_desktop_project_root(tmp_path / "project")
    report_path = tmp_path / "diagnostics.json"
    data_dir = tmp_path / "desktop-data"

    exit_code = desktop_main(
        [
            "--diagnostics",
            "--project-root",
            str(project_root),
            "--report-json",
            str(report_path),
            "--data-dir",
            str(data_dir),
            "--project-id",
            "desktop-diagnostics",
        ]
    )

    assert exit_code == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["counts"]["error"] == 0
    assert payload["overall_status"] in {"ok", "warning"}
    assert (data_dir / "agent.sqlite3").exists()


def test_desktop_app_source_exposes_provider_settings_controls():
    source = (ROOT / "src" / "consensus_translation" / "desktop_agent_app.py").read_text(
        encoding="utf-8"
    )

    assert "Provider ID" in source
    assert "Base URL" in source
    assert "Model" in source
    assert "API Key" in source
    assert "Save Provider" in source
    assert "Load Providers" in source
    assert "Smoke Providers" in source
    assert "Run Diagnostics" in source
    assert "Run Local Smoke" in source
    assert "Open OCR Image" in source
    assert "Import Hook Text" in source
    assert "Training Set" in source
    assert "Validation Set" in source
    assert "Evaluator" in source
    assert "Tesseract" in source
    assert "COMET Command" in source
    assert "Upload Training" in source
