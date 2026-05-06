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


class TrainingPanel(QWidget):
    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client

        self.raw_file_path = ""
        self.reference_file_path = ""
        self.workflow_id = ""

        self.raw_file_input = QLineEdit(self)
        self.raw_file_input.setReadOnly(True)
        self.reference_file_input = QLineEdit(self)
        self.reference_file_input.setReadOnly(True)

        self.source_combo = QComboBox(self)
        self.source_combo.setEditable(True)
        self.source_combo.addItems(["主题", "yu_gi_oh", "default"])

        self.pick_raw_button = QPushButton("选择原文", self)
        self.pick_reference_button = QPushButton("选择参照", self)
        self.start_button = QPushButton("开始", self)
        self.reconcile_button = QPushButton("对账", self)
        self.commit_button = QPushButton("提交", self)

        self.pick_raw_button.clicked.connect(self.pick_raw_file)
        self.pick_reference_button.clicked.connect(self.pick_reference_file)
        self.start_button.clicked.connect(self.start_workflow)
        self.reconcile_button.clicked.connect(self.reconcile_workflow)
        self.commit_button.clicked.connect(self.commit_workflow)

        form = QFormLayout()
        form.addRow("原文文件", self.raw_file_input)
        form.addRow("参照文件(可选)", self.reference_file_input)
        form.addRow("来源声明", self.source_combo)

        actions = QHBoxLayout()
        actions.addWidget(self.pick_raw_button)
        actions.addWidget(self.pick_reference_button)
        actions.addWidget(self.start_button)
        actions.addWidget(self.reconcile_button)
        actions.addWidget(self.commit_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)

    def pick_raw_file(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择原文文件", "", "Text Files (*.txt *.md)")
        if file_path:
            self.raw_file_path = file_path
            self.raw_file_input.setText(file_path)
        return self.raw_file_path

    def pick_reference_file(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(self, "选择参照文件", "", "Text Files (*.txt *.md)")
        if file_path:
            self.reference_file_path = file_path
            self.reference_file_input.setText(file_path)
        return self.reference_file_path

    def start_workflow(self) -> dict[str, object]:
        if not self.raw_file_path.strip():
            return {}
        payload = self.api_client.start_training_workflow(
            raw_file_path=self.raw_file_path,
            source_declaration=self.source_combo.currentText(),
            reference_file_path=self.reference_file_path or None,
        )
        self.workflow_id = str(payload.get("workflow_id", ""))
        return payload

    def reconcile_workflow(self) -> dict[str, object]:
        workflow_id = self.workflow_id.strip()
        if not workflow_id:
            return {}
        return self.api_client.reconcile_training_workflow(workflow_id)

    def commit_workflow(self) -> dict[str, object]:
        workflow_id = self.workflow_id.strip()
        if not workflow_id:
            return {}
        return self.api_client.commit_training_workflow(workflow_id)
