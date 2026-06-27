from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
)


class LexiconPage(QWidget):
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

        title = QLabel("词库与风格", self)
        title.setObjectName("pageTitle")
        self.pending_list = QListWidget(self)
        self.export_view = QTextEdit(self)
        self.export_view.setReadOnly(True)
        self.status_label = QLabel("就绪", self)
        self.refresh_button = QPushButton("刷新待确认词条", self)
        self.confirm_button = QPushButton("确认选中词条", self)
        self.refresh_button.clicked.connect(self.refresh)
        self.confirm_button.clicked.connect(self.confirm_selected_update)

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.confirm_button)
        buttons.addWidget(self.status_label, 1)

        layout.addWidget(title)
        layout.addWidget(self.pending_list, 1)
        layout.addWidget(self.export_view, 1)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        self.pending_list.clear()
        for update in self.service.list_pending_lexicon_updates():
            event_id = int(update["id"])
            text = (
                f"#{event_id} | {update['topic']} | {update['layer']} | "
                f"{update['source']} -> {update['target']}"
            )
            self.pending_list.addItem(text)
            self.pending_list.item(self.pending_list.count() - 1).setData(
                Qt.UserRole,
                event_id,
            )
        self._render_export()
        self.status_label.setText(f"待确认：{self.pending_list.count()}")

    def confirm_selected_update(self) -> None:
        item = self.pending_list.currentItem()
        if item is None:
            self.status_label.setText("请选择词条")
            return
        event_id = int(item.data(Qt.UserRole))
        if self.service.confirm_lexicon_update(event_id):
            self.status_label.setText(f"已确认：#{event_id}")
        else:
            self.status_label.setText(f"未找到：#{event_id}")
        self.refresh()

    def _render_export(self) -> None:
        payload = self.service.export_current_topic_lexicon()
        self.export_view.setPlainText(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        )
