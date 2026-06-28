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


def test_history_and_settings_pages_use_service_state(qtbot, qt_service, tmp_path):
    window = MainWindow(controller=qt_service, data_root=tmp_path)
    qtbot.addWidget(window)
    settings_page = window.page("设置")
    history_page = window.page("历史")

    settings = qt_service.load_user_settings().with_changes(
        default_source_language="en",
        default_target_language="ja",
        default_mode="learning",
        budget_limit=2.5,
        auto_save_history=False,
    )
    qt_service.save_user_settings(settings)
    settings_page.refresh()

    assert settings_page.budget_limit_input.value() == 2.5
    assert settings_page.auto_save_history_checkbox.isChecked() is False

    qt_service.save_translation_history(
        source_text="Leviathan wakes",
        translated_text="リヴァイアサンが目覚める",
        source_language="en",
        target_language="ja",
        topic="myth",
        mode="learning",
        run_id="run-history-1",
        workflow_status="awaiting_human_confirmation",
        workflow_steps=("workflow:localTranslating", "workflow:waitingHumanConfirmation"),
        consensus_score=0.71,
        confidence_level="medium",
        conflicts=("candidate_divergence",),
        arbitration_reason="localProviderA kept higher confidence overlap",
        requires_human_review=True,
    )
    history_page.refresh()

    assert history_page.history_list.count() == 1
    assert "run-history-1" in history_page.history_list.item(0).text()

    qt_service.clear_translation_history()
    history_page.refresh()

    assert history_page.history_list.count() == 0


def test_history_page_refills_registered_workbench_page(qtbot, qt_service, tmp_path):
    from consensus_translation.desktop_qt.navigation import NAVIGATION_LABELS

    window = MainWindow(controller=qt_service, data_root=tmp_path)
    qtbot.addWidget(window)
    workbench_label = NAVIGATION_LABELS[2]
    history_label = NAVIGATION_LABELS[8]
    workbench_page = window.page(workbench_label)
    history_page = window.page(history_label)

    qt_service.save_translation_history(
        source_text="Leviathan wakes",
        translated_text="JP:Leviathan wakes",
        source_language="en",
        target_language="ja",
        topic="myth",
        mode="learning",
        run_id="run-history-load",
        workflow_status="awaiting_human_confirmation",
    )
    history_page.refresh()
    history_page.history_list.setCurrentRow(0)

    history_page.use_selected()

    assert window.current_page() is workbench_page
    assert workbench_page.source_editor.toPlainText() == "Leviathan wakes"
    assert workbench_page.result_editor.toPlainText() == "JP:Leviathan wakes"
    assert workbench_page.source_lang_input.text() == "en"
    assert workbench_page.target_lang_input.text() == "ja"
    assert workbench_page.topic_input.text() == "myth"
    assert workbench_page.mode_input.currentText() == "learning"
    assert workbench_page._last_run_id == "run-history-load"


def test_qt_service_imports_exports_lexicon_and_skips_rating_without_record(
    qt_service,
    tmp_path,
):
    store = qt_service.controller.store
    store.upsert_lexicon_entry(
        "release-test",
        "terms",
        "Aether Core",
        "エーテルコア",
        note="approved spelling",
        confidence=0.94,
        entry_source="manual_edit",
        confirmed_by_user=True,
        is_special=True,
    )
    export_path = tmp_path / "lexicon-export.json"

    qt_service.export_lexicon_to_file(export_path)
    imported_service = DesktopApplicationService(data_root=tmp_path / "imported")
    counts = imported_service.import_lexicon_from_file(export_path)

    assert counts == {"terms": 1, "phrases": 0, "style_rules": 0}
    imported_entries = imported_service.controller.store.export_all_lexicon_entries()
    imported_term = imported_entries["release-test"]["terms"]["Aether Core"]
    assert imported_term["target"] == "\u30a8\u30fc\u30c6\u30eb\u30b3\u30a2"
    assert imported_term["is_special"] is True

    assert qt_service.skip_translation_rating("run-without-rating") is None
    assert store.list_translation_ratings() == []
