from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.agent_input_plugins import FolderInboxInputPlugin
from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
)


class ConnectorsPage(QWidget):
    def __init__(
        self,
        service: DesktopApplicationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("输入连接器", self)
        title.setObjectName("pageTitle")
        description = QLabel(
            "通过文件夹收件箱、剪贴板/OCR 边界接入 Textractor、LunaTranslator、GalTransl 等工具输出。",
            self,
        )
        description.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(description)

        folder_row = QHBoxLayout()
        self.folder_path_input = QLineEdit(
            str(self.service.data_root / "connector-inbox"),
            self,
        )
        self.browse_button = QPushButton("选择文件夹", self)
        self.capture_button = QPushButton("读取收件箱", self)
        self.browse_button.clicked.connect(self.choose_folder)
        self.capture_button.clicked.connect(self.capture_folder)
        folder_row.addWidget(self.folder_path_input, 1)
        folder_row.addWidget(self.browse_button)
        folder_row.addWidget(self.capture_button)
        layout.addLayout(folder_row)

        self.capture_list = QListWidget(self)
        self.content_preview = QPlainTextEdit(self)
        self.content_preview.setReadOnly(True)
        self.status_label = QLabel("就绪", self)
        layout.addWidget(self.capture_list, 1)
        layout.addWidget(self.content_preview, 1)
        layout.addWidget(self.status_label)

    def choose_folder(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择连接器收件箱",
            self.folder_path_input.text(),
        )
        if directory:
            self.folder_path_input.setText(directory)

    def capture_folder(self):
        inbox = Path(self.folder_path_input.text()).expanduser()
        plugin = FolderInboxInputPlugin(inbox)
        captured = plugin.capture()
        self.capture_list.clear()
        self.content_preview.clear()
        for item in captured:
            self.capture_list.addItem(f"{Path(item.input_ref).name} | {len(item.text)} 字符")
            self.capture_list.item(self.capture_list.count() - 1).setData(
                Qt.UserRole,
                item.text,
            )
        if captured:
            self.capture_list.setCurrentRow(0)
            self.content_preview.setPlainText(captured[0].text)
        self.status_label.setText(f"读取：{len(captured)}")
        self.capture_list.currentRowChanged.connect(self._render_selected)
        return captured

    def _render_selected(self, row: int) -> None:
        if row < 0:
            return
        item = self.capture_list.item(row)
        if item is not None:
            self.content_preview.setPlainText(str(item.data(Qt.UserRole)))
