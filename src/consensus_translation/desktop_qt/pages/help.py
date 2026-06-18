from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.help_content import HelpIndex


class HelpPage(QWidget):
    def __init__(
        self,
        service: object | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.help_index = HelpIndex.load_default()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("帮助中心", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("搜索：Textractor、Provider、Tesseract、隐私、许可…")
        self.search_button = QPushButton("搜索", self)
        self.search_button.clicked.connect(self.search)
        self.search_input.returnPressed.connect(self.search)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        splitter = QSplitter(Qt.Horizontal, self)
        self.results_list = QListWidget(splitter)
        self.content_view = QPlainTextEdit(splitter)
        self.content_view.setReadOnly(True)
        splitter.addWidget(self.results_list)
        splitter.addWidget(self.content_view)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.results_list.currentRowChanged.connect(self._render_selected)
        self._load_topics()

    def _load_topics(self) -> None:
        self.results_list.clear()
        for topic in self.help_index.topics():
            self.results_list.addItem(f"{topic.title} · {topic.topic_id}")
            self.results_list.item(self.results_list.count() - 1).setData(
                Qt.UserRole,
                topic.topic_id,
            )
        self.results_list.setCurrentRow(0)

    def search(self) -> None:
        results = self.help_index.search(self.search_input.text())
        self.results_list.clear()
        for result in results:
            self.results_list.addItem(f"{result.title} · {result.topic_id}")
            self.results_list.item(self.results_list.count() - 1).setData(
                Qt.UserRole,
                result.topic_id,
            )
        if results:
            self.results_list.setCurrentRow(0)
        else:
            self.content_view.setPlainText("没有找到匹配内容。")

    def _render_selected(self, row: int) -> None:
        if row < 0:
            return
        item = self.results_list.item(row)
        if item is None:
            return
        topic = self.help_index.get(str(item.data(Qt.UserRole)))
        self.content_view.setPlainText(topic.markdown)
