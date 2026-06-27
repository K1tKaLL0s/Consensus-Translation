from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_react_workspace_resolves_built_vite_entrypoint():
    from consensus_translation.desktop_qt.react_workspace import (
        react_dist_status,
        resolve_react_dist_index,
    )

    index_path = resolve_react_dist_index(ROOT)
    status = react_dist_status(ROOT)

    assert index_path == ROOT / "UI design" / "High-Fidelity Translation Software UI" / "dist" / "index.html"
    assert status["path"] == str(index_path)
    assert status["status"] in {"available", "missing"}


def test_react_workspace_resolves_packaged_internal_dist(monkeypatch, tmp_path):
    from consensus_translation.desktop_qt.react_workspace import resolve_react_dist_index

    app_dir = tmp_path / "ConsensusTranslationAgent"
    internal_index = app_dir / "_internal" / "react-ui-dist" / "index.html"
    internal_index.parent.mkdir(parents=True)
    internal_index.write_text("<!doctype html>", encoding="utf-8")
    executable = app_dir / "ConsensusTranslationAgent.exe"
    executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert resolve_react_dist_index(ROOT) == internal_index


def test_qt_packaging_includes_react_dist_and_webengine_imports():
    spec_text = (ROOT / "packaging" / "desktop_agent_qt.spec").read_text(encoding="utf-8")

    assert "High-Fidelity Translation Software UI\" / \"dist" in spec_text
    assert "react-ui-dist" in spec_text
    assert "PySide6.QtWebEngineWidgets" in spec_text
    assert "PySide6.QtWebChannel" in spec_text
    assert "consensus_translation.desktop_qt.react_workspace" in spec_text


def test_react_bridge_exposes_contract_dto_methods(qtbot, tmp_path):
    import json
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from consensus_translation.agent_credentials import LocalCredentialStore
    from consensus_translation.agent_providers import EchoModelProvider
    from consensus_translation.agent_store import AgentRunStore
    from consensus_translation.desktop_agent_app import (
        DesktopAgentConfig,
        DesktopAgentController,
    )
    from consensus_translation.desktop_qt.application_service import (
        DesktopApplicationService,
    )
    from consensus_translation.desktop_qt.react_bridge import ReactContractBridge

    controller = DesktopAgentController(
        DesktopAgentConfig(
            source_lang="en",
            target_lang="ja",
            topic="bridge-test",
            allow_mock_providers=True,
        ),
        providers=[EchoModelProvider("local-preview", prefix="JA:")],
        store=AgentRunStore(tmp_path / "agent.sqlite3"),
    )
    service = DesktopApplicationService(
        controller=controller,
        credential_store=LocalCredentialStore(tmp_path / "credentials.json"),
        data_root=tmp_path,
    )
    bridge = ReactContractBridge(service)

    capabilities = json.loads(bridge.getCapabilities())
    result = json.loads(
        bridge.translateText(
            json.dumps(
                {
                    "text": "alpha beta",
                    "source_lang": "en",
                    "target_lang": "ja",
                    "topic": "bridge-test",
                    "mode": "learning",
                }
            )
        )
    )

    assert set(capabilities) >= {"text_translation", "self_decision", "mock_provider"}
    assert result["task_status"] in {"awaiting_confirmation", "completed"}
    assert result["consensus"]["final_text"] == "JA:alpha beta"
    assert result["consensus"]["alignment_level"] == "heuristic"


def test_react_workspace_registers_webchannel_bridge_in_webengine_host():
    text = (ROOT / "src" / "consensus_translation" / "desktop_qt" / "react_workspace.py").read_text(
        encoding="utf-8"
    )

    assert "QWebChannel" in text
    assert "ReactContractBridge" in text
    assert "consensusTranslationBridge" in text
    assert "qrc:///qtwebchannel/qwebchannel.js" in text


def test_react_main_workspace_routes_translation_through_bridge_not_static_mock():
    text = (
        ROOT
        / "UI design"
        / "High-Fidelity Translation Software UI"
        / "src"
        / "app"
        / "pages"
        / "MainWorkspace.tsx"
    ).read_text(encoding="utf-8")

    assert "translate_text(" in text
    assert "is_backend_bridge_available" in text
    assert "Product intro.docx" not in text
    assert "Feature screen.png" not in text
    assert "Translation complete" not in text
    assert "Lingua Agent is an intelligent translation tool" not in text


def test_react_main_workspace_standard_translation_uses_contract_mode_and_target_state():
    text = (
        ROOT
        / "UI design"
        / "High-Fidelity Translation Software UI"
        / "src"
        / "app"
        / "pages"
        / "MainWorkspace.tsx"
    ).read_text(encoding="utf-8")

    assert 'mode: "learning"' not in text
    assert 'target_lang: "en"' not in text
    assert "selectedTargetLang" in text
    assert "TARGET_LANGUAGES" in text


def test_react_backend_bridge_exposes_backend_contract_methods_needed_by_ui():
    bridge_text = (
        ROOT
        / "UI design"
        / "High-Fidelity Translation Software UI"
        / "src"
        / "contracts"
        / "backend_bridge.ts"
    ).read_text(encoding="utf-8")

    for method_name in (
        "getSelfDecisionStatus",
        "getProviderHealth",
        "previewRemoteCalls",
    ):
        assert method_name in bridge_text
    for function_name in (
        "get_self_decision_status(",
        "get_provider_health(",
        "preview_remote_calls(",
    ):
        assert function_name in bridge_text


def test_react_learning_mode_loads_self_decision_eligibility_from_backend():
    text = (
        ROOT
        / "UI design"
        / "High-Fidelity Translation Software UI"
        / "src"
        / "app"
        / "pages"
        / "LearningMode.tsx"
    ).read_text(encoding="utf-8")

    assert "get_self_decision_status" in text
    assert "useEffect" in text
    assert "setSelfDecision" in text


def test_react_unwired_history_and_detail_actions_are_disabled_or_handled():
    react_root = ROOT / "UI design" / "High-Fidelity Translation Software UI" / "src"
    history_text = (react_root / "app" / "pages" / "History.tsx").read_text(
        encoding="utf-8"
    )
    detail_text = (react_root / "app" / "pages" / "TranslationDetail.tsx").read_text(
        encoding="utf-8"
    )

    assert "History search is not exposed in the backend contract." in history_text
    assert "History filtering is not exposed in the backend contract." in history_text
    assert "History deletion is available in the Windows workbench." in history_text
    assert "Re-translate is available from the Windows workbench." in detail_text
    assert "Detail export is available from the Windows workbench." in detail_text
    assert "navigator.clipboard.writeText" in detail_text


def test_react_backend_owned_pages_do_not_render_static_backend_records():
    react_root = ROOT / "UI design" / "High-Fidelity Translation Software UI" / "src"
    pages = [
        react_root / "app" / "components" / "Sidebar.tsx",
        react_root / "app" / "pages" / "History.tsx",
        react_root / "app" / "pages" / "TranslationDetail.tsx",
        react_root / "app" / "pages" / "TermbaseManagement.tsx",
        react_root / "app" / "pages" / "LearningMode.tsx",
        react_root / "app" / "pages" / "ApiConfig.tsx",
        react_root / "app" / "pages" / "DataPrivacy.tsx",
        react_root / "app" / "pages" / "ExportTermbase.tsx",
        react_root / "app" / "pages" / "Settings.tsx",
        react_root / "app" / "pages" / "AppearanceSettings.tsx",
    ]

    forbidden = (
        "../data/contractData",
        "Product_Manual_training.docx",
        "Product_Manual_validation.docx",
        "Archived translation",
        "function module",
        "translation memory",
        "sk-",
        "312 items",
        "45 items",
        "198 items",
        "42.5 MB",
        "Version 2.4.1",
        "96%",
        "87%",
        "1,086 reviewed",
    )
    for page in pages:
        text = page.read_text(encoding="utf-8")
        for item in forbidden:
            assert item not in text
    backend_bridge = (react_root / "contracts" / "backend_bridge.ts").read_text(
        encoding="utf-8"
    )
    for function_name in (
        "list_history(",
        "get_termbase(",
        "save_provider_settings(",
        "smoke_providers(",
    ):
        assert function_name in backend_bridge


def test_main_window_exposes_react_workspace_page_when_dist_exists(qtbot, tmp_path):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from consensus_translation.agent_credentials import LocalCredentialStore
    from consensus_translation.agent_providers import EchoModelProvider
    from consensus_translation.agent_store import AgentRunStore
    from consensus_translation.desktop_agent_app import (
        DesktopAgentConfig,
        DesktopAgentController,
    )
    from consensus_translation.desktop_qt.application_service import (
        DesktopApplicationService,
    )
    from consensus_translation.desktop_qt.main_window import MainWindow

    controller = DesktopAgentController(
        DesktopAgentConfig(allow_mock_providers=True),
        providers=[EchoModelProvider("local-preview")],
        store=AgentRunStore(tmp_path / "agent.sqlite3"),
    )
    service = DesktopApplicationService(
        controller=controller,
        credential_store=LocalCredentialStore(tmp_path / "credentials.json"),
        data_root=tmp_path,
    )
    window = MainWindow(controller=service, data_root=tmp_path)
    qtbot.addWidget(window)

    page = window.page("React 工作区")

    assert page is not None
    assert hasattr(page, "react_status")
