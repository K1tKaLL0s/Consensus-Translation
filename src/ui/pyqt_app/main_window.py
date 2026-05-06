import socket

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.pyqt_app.api_client import ApiClient
from src.ui.pyqt_app.panels import LLMPanel, ResultPanel, TrainingPanel, TranslatePanel
from src.ui.pyqt_app.state_store import WorkflowStateStore


def offline_notice_text() -> str:
    return "当前未联网，部分功能受限。"


def network_available(timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except OSError:
        return False


class MainWindow(QMainWindow):
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000") -> None:
        super().__init__()
        self.setWindowTitle("MAATCS 三联屏控制台")

        self.state_store = WorkflowStateStore(api_base_url=api_base_url)
        self.api_client = ApiClient(base_url=self.state_store.api_base_url)

        self.api_base_url_input = QLineEdit(self.state_store.api_base_url)
        self.apply_api_base_url_button = QPushButton("应用")
        self.apply_api_base_url_button.clicked.connect(self.apply_api_base_url)

        top_controls = QHBoxLayout()
        top_controls.addWidget(QLabel("API Base URL"))
        top_controls.addWidget(self.api_base_url_input)
        top_controls.addWidget(self.apply_api_base_url_button)

        self.tabs = self.build_interactive_tabs()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addLayout(top_controls)
        layout.addWidget(self.tabs)

        self.setCentralWidget(container)
        self.statusBar().showMessage("就绪")
        self.offline_notice_box: QMessageBox | None = None

        if not network_available():
            warning = offline_notice_text()
            self.statusBar().showMessage(warning)
            notice = QMessageBox(self)
            notice.setIcon(QMessageBox.Icon.Warning)
            notice.setWindowTitle("网络状态")
            notice.setText(warning)
            notice.setStandardButtons(QMessageBox.StandardButton.Ok)
            notice.setWindowModality(Qt.WindowModality.NonModal)
            notice.setModal(False)
            notice.show()
            self.offline_notice_box = notice

    def build_interactive_tabs(self) -> QTabWidget:
        tabs = QTabWidget(self)

        self.translate_panel = TranslatePanel(api_client=self.api_client, state_store=self.state_store, parent=tabs)
        self.training_panel = TrainingPanel(api_client=self.api_client, parent=tabs)
        self.llm_panel = LLMPanel(api_client=self.api_client, parent=tabs)
        self.result_panel = ResultPanel(parent=tabs)

        tabs.addTab(self.translate_panel, "翻译")
        tabs.addTab(self.training_panel, "训练")
        tabs.addTab(self.llm_panel, "模型")
        tabs.addTab(self.result_panel, "结果")

        return tabs

    def apply_api_base_url(self) -> None:
        updated_url = self.api_base_url_input.text().strip().rstrip("/")
        if not updated_url:
            return
        self.state_store.api_base_url = updated_url
        self.api_client.base_url = updated_url


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 700)
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
