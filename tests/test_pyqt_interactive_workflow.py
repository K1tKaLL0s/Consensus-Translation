import os

import pytest

from src.ui.pyqt_app.api_client import ApiClient
from src.ui.pyqt_app.panels.training_panel import TrainingPanel
from src.ui.pyqt_app.panels.translate_panel import TranslatePanel
from src.ui.pyqt_app.panels.result_panel import ResultPanel
from src.ui.pyqt_app.state_store import WorkflowStateStore


def test_workflow_state_store_locks_copy_until_confirmed() -> None:
    store = WorkflowStateStore()

    store.set_translate_state(
        workflow_id="wf-1",
        stage="revised",
        latest_text="draft",
        confirmed=False,
    )
    assert store.workflow_id == "wf-1"
    assert store.stage == "revised"
    assert store.latest_text == "draft"
    assert store.copy_allowed is False

    store.set_translate_state(
        workflow_id="wf-1",
        stage="confirmed",
        latest_text="final",
        confirmed=True,
    )
    assert store.copy_allowed is True


def test_api_client_uses_local_default_base_url() -> None:
    client = ApiClient()
    assert client.base_url == "http://127.0.0.1:8000"


def test_result_panel_copy_button_follows_copy_allowed(qt_app) -> None:
    panel = ResultPanel()
    panel.set_copy_allowed(False)
    assert panel.copy_button.isEnabled() is False

    panel.set_copy_allowed(True)
    assert panel.copy_button.isEnabled() is True


class _TranslateApiStub:
    def __init__(self) -> None:
        self.start_calls = 0
        self.revise_calls = 0
        self.confirm_calls = 0

    def start_translate_workflow(self, file_path: str, source_declaration: str) -> dict[str, object]:
        self.start_calls += 1
        return {"workflow_id": "wf-1", "status": "translate_started", "translated_text": "draft", "copy_allowed": False}

    def revise_translate_workflow(self, workflow_id: str, user_revision_text: str) -> dict[str, object]:
        self.revise_calls += 1
        return {"workflow_id": workflow_id, "status": "translate_revised", "user_revision_text": user_revision_text}

    def confirm_translate_workflow(self, workflow_id: str, confirmed: bool = True) -> dict[str, object]:
        self.confirm_calls += 1
        return {"workflow_id": workflow_id, "status": "translate_confirmed"}


class _TrainingApiStub:
    def __init__(self) -> None:
        self.start_calls = 0
        self.reconcile_calls = 0
        self.commit_calls = 0

    def start_training_workflow(
        self,
        raw_file_path: str,
        source_declaration: str,
        reference_file_path: str | None = None,
    ) -> dict[str, object]:
        self.start_calls += 1
        return {"workflow_id": "twf-1"}

    def reconcile_training_workflow(self, workflow_id: str) -> dict[str, object]:
        self.reconcile_calls += 1
        return {"workflow_id": workflow_id, "status": "reconciled"}

    def commit_training_workflow(self, workflow_id: str) -> dict[str, object]:
        self.commit_calls += 1
        return {"workflow_id": workflow_id, "status": "committed"}


def test_translate_panel_skips_start_revise_confirm_without_required_inputs(qt_app) -> None:
    store = WorkflowStateStore()
    api = _TranslateApiStub()
    panel = TranslatePanel(api_client=api, state_store=store)

    assert panel.start_workflow() == {}
    assert api.start_calls == 0

    panel.revision_input.setText("rev")
    assert panel.revise_workflow() == {}
    assert api.revise_calls == 0

    assert panel.confirm_workflow() == {}
    assert api.confirm_calls == 0


def test_translate_confirm_defaults_copy_allowed_true_when_payload_omits_field(qt_app) -> None:
    store = WorkflowStateStore(workflow_id="wf-1", stage="translate_revised", copy_allowed=False, latest_text="latest")
    api = _TranslateApiStub()
    panel = TranslatePanel(api_client=api, state_store=store)

    payload = panel.confirm_workflow()

    assert payload["status"] == "translate_confirmed"
    assert api.confirm_calls == 1
    assert store.copy_allowed is True


def test_training_panel_skips_start_reconcile_commit_without_required_inputs(qt_app) -> None:
    api = _TrainingApiStub()
    panel = TrainingPanel(api_client=api)

    assert panel.start_workflow() == {}
    assert api.start_calls == 0

    panel.workflow_id = ""
    assert panel.reconcile_workflow() == {}
    assert api.reconcile_calls == 0

    assert panel.commit_workflow() == {}
    assert api.commit_calls == 0


@pytest.fixture
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
