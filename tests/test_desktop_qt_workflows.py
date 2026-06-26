import os
from pathlib import Path
import sys

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import Qt

from consensus_translation.agent_diagnostics import DiagnosticReport
from consensus_translation.agent_credentials import LocalCredentialStore
from consensus_translation.agent_providers import EchoModelProvider
from consensus_translation.agent_providers import StaticModelProvider
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.desktop_agent_app import (
    DesktopAgentConfig,
    DesktopAgentController,
)
from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
)
from consensus_translation.desktop_qt.main_window import MainWindow


@pytest.fixture
def qt_service(tmp_path):
    store = AgentRunStore(tmp_path / "agent.sqlite3")
    credential_store = LocalCredentialStore(tmp_path / "credentials.json")
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="ja",
            topic="release-test",
            max_context_tokens=128,
            reserved_output_tokens=16,
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("local-a", prefix="JP:")],
        store=store,
    )
    return DesktopApplicationService(
        controller=controller,
        credential_store=credential_store,
        data_root=tmp_path,
    )


@pytest.fixture
def qt_remote_service(tmp_path):
    store = AgentRunStore(tmp_path / "remote-agent.sqlite3")
    credential_store = LocalCredentialStore(tmp_path / "remote-credentials.json")
    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="ja",
            topic="remote-test",
            mode="learning",
            api_enabled=True,
            budget_limit=1.0,
            max_context_tokens=128,
            reserved_output_tokens=16,
        ),
        providers=[
            StaticModelProvider(
                "remote-a",
                "リモート翻訳",
                confidence=0.9,
                estimated_cost=0.25,
                requires_api=True,
            )
        ],
        store=store,
    )
    return DesktopApplicationService(
        controller=controller,
        credential_store=credential_store,
        data_root=tmp_path,
    )


def test_workbench_translates_and_renders_result(qtbot, qt_service, tmp_path):
    window = MainWindow(controller=qt_service, data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.show_page("翻译工作台")
    page = window.current_page()
    page.source_editor.setPlainText("alpha beta")

    qtbot.mouseClick(page.translate_button, Qt.LeftButton)

    assert page.result_editor.toPlainText() == "JP:alpha beta"
    assert page.status_label.text() in {"已完成", "等待人工确认"}


def test_qt_service_uses_installed_diagnostics_mode_when_frozen(
    qt_service,
    monkeypatch,
):
    captured = {}

    def fake_run_diagnostics(credential_store, mode):
        captured["mode"] = mode
        return DiagnosticReport(
            overall_status="ok",
            checks=[],
            counts={"ok": 0, "warning": 0, "error": 0},
        )

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(qt_service.controller, "run_diagnostics", fake_run_diagnostics)

    lines = qt_service.run_diagnostics()

    assert captured["mode"] == "installed"
    assert lines[0].startswith("diagnostics: ok")


def test_workbench_preflights_remote_calls_and_exports_artifacts(
    qtbot,
    qt_remote_service,
    tmp_path,
):
    window = MainWindow(controller=qt_remote_service, data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.show_page("翻译工作台")
    page = window.current_page()
    page.source_editor.setPlainText("alpha beta")

    qtbot.mouseClick(page.preview_button, Qt.LeftButton)
    assert "remote calls: 1" in page.preflight_view.toPlainText()

    qtbot.mouseClick(page.translate_button, Qt.LeftButton)
    assert "remote preflight confirmation required" in page.result_editor.toPlainText()

    qtbot.mouseClick(page.confirm_remote_button, Qt.LeftButton)
    qtbot.mouseClick(page.translate_button, Qt.LeftButton)

    assert page.result_editor.toPlainText() == "リモート翻訳"
    artifacts = page.export_artifacts(tmp_path / "exports")
    assert artifacts["final_text"].read_text(encoding="utf-8") == "リモート翻訳"


def test_workbench_loads_source_file_and_records_recent_file(
    qtbot,
    qt_service,
    tmp_path,
):
    source_file = tmp_path / "scene.txt"
    source_file.write_text("file input", encoding="utf-8")
    window = MainWindow(controller=qt_service, data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.show_page("翻译工作台")
    page = window.current_page()

    page.load_source_file(source_file)
    qtbot.mouseClick(page.translate_button, Qt.LeftButton)

    assert page.result_editor.toPlainText() == "JP:file input"
    profile = qt_service.controller.load_project_profile()
    assert profile is not None
    assert str(source_file) in profile.recent_files


def test_provider_save_never_displays_secret(qtbot, qt_service, tmp_path):
    window = MainWindow(controller=qt_service, data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    page = window.page("Provider 与评估器")
    page.provider_id_input.setText("remote-a")
    page.base_url_input.setText("https://api.example.test/v1")
    page.model_input.setText("translator")
    page.api_key_input.setText("sk-test-secret")

    qtbot.mouseClick(page.save_button, Qt.LeftButton)

    assert "sk-test-secret" not in window.visible_text()
    assert page.api_key_input.text() == ""
    assert "remote-a" in page.status_label.text()


def test_project_and_lexicon_pages_render_controller_state(qtbot, qt_service, tmp_path):
    qt_service.translate_text("Leviathan")
    window = MainWindow(controller=qt_service, data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    project_page = window.page("项目与任务")
    project_page.refresh()
    assert project_page.runs_list.count() == 1
    assert "awaiting_human_confirmation" in project_page.runs_list.item(0).text()

    lexicon_page = window.page("词库与风格")
    lexicon_page.refresh()
    assert lexicon_page.pending_list.count() == 1
    assert "Leviathan" in lexicon_page.pending_list.item(0).text()

    lexicon_page.pending_list.setCurrentRow(0)
    qtbot.mouseClick(lexicon_page.confirm_button, Qt.LeftButton)

    assert lexicon_page.pending_list.count() == 0
    assert "Leviathan" in lexicon_page.export_view.toPlainText()
