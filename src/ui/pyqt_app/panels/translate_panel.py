from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.pyqt_app.api_client import ApiClient
from src.ui.pyqt_app.state_store import WorkflowStateStore


class TranslatePanel(QWidget):
    def __init__(self, api_client: ApiClient, state_store: WorkflowStateStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.state_store = state_store
        self.selected_file_path = ""

        self.file_path_input = QLineEdit(self)
        self.file_path_input.setReadOnly(True)
        self.pick_file_button = QPushButton("选择文件", self)

        self.source_combo = QComboBox(self)
        self.source_combo.setEditable(True)
        self.source_combo.addItems(["主题", "yu_gi_oh", "default"])

        self.revision_input = QLineEdit(self)

        self.start_button = QPushButton("开始", self)
        self.revise_button = QPushButton("修订", self)
        self.confirm_button = QPushButton("确认", self)

        self.pick_file_button.clicked.connect(self.pick_file)
        self.start_button.clicked.connect(self.start_workflow)
        self.revise_button.clicked.connect(self.revise_workflow)
        self.confirm_button.clicked.connect(self.confirm_workflow)

        form = QFormLayout()
        form.addRow("文件", self.file_path_input)
        form.addRow("来源声明", self.source_combo)
        form.addRow("修订文本", self.revision_input)

        actions = QHBoxLayout()
        actions.addWidget(self.pick_file_button)
        actions.addWidget(self.start_button)
        actions.addWidget(self.revise_button)
        actions.addWidget(self.confirm_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)

    def pick_file(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文本文件", "", "Text Files (*.txt *.md)")
        if file_path:
            self.selected_file_path = file_path
            self.file_path_input.setText(file_path)
        return self.selected_file_path

    def start_workflow(self) -> dict[str, object]:
        if not self.selected_file_path.strip():
            return {}
        payload = self.api_client.start_translate_workflow(
            file_path=self.selected_file_path,
            source_declaration=self.source_combo.currentText(),
        )
        self.state_store.set_translate_state(
            workflow_id=str(payload.get("workflow_id", "")),
            stage=str(payload.get("status", "translate_started")),
            latest_text=str(payload.get("translated_text", "")),
            confirmed=bool(payload.get("copy_allowed", False)),
        )
        return payload

    def revise_workflow(self) -> dict[str, object]:
        workflow_id = (self.state_store.workflow_id or "").strip()
        if not workflow_id:
            return {}
        payload = self.api_client.revise_translate_workflow(
            workflow_id=workflow_id,
            user_revision_text=self.revision_input.text(),
        )
        self.state_store.set_translate_state(
            workflow_id=str(payload.get("workflow_id", self.state_store.workflow_id or "")),
            stage=str(payload.get("status", "translate_revised")),
            latest_text=str(payload.get("user_revision_text", self.revision_input.text())),
            confirmed=bool(payload.get("copy_allowed", False)),
        )
        return payload

    def confirm_workflow(self) -> dict[str, object]:
        workflow_id = (self.state_store.workflow_id or "").strip()
        if not workflow_id:
            return {}
        payload = self.api_client.confirm_translate_workflow(workflow_id=workflow_id, confirmed=True)
        self.state_store.set_translate_state(
            workflow_id=str(payload.get("workflow_id", self.state_store.workflow_id or "")),
            stage=str(payload.get("status", "translate_confirmed")),
            latest_text=self.state_store.latest_text,
            confirmed=bool(payload.get("copy_allowed", True)),
        )
        return payload
