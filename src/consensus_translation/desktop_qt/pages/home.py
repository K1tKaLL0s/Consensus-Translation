from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
    join_lines,
)


class HomePage(QWidget):
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

        title = QLabel("首页", self)
        title.setObjectName("pageTitle")
        self.summary_view = QTextEdit(self)
        self.summary_view.setReadOnly(True)
        self.refresh_button = QPushButton("刷新项目状态", self)
        self.refresh_button.clicked.connect(self.refresh)

        layout.addWidget(title)
        layout.addWidget(self.summary_view)
        layout.addWidget(self.refresh_button)
        self.refresh()

    def refresh(self) -> None:
        lines = [
            "共识翻译 Agent 桌面版",
            "操作逻辑：输入 → 预检 → 翻译 → 人工确认 → 词库写回 → 导出。",
            "",
            *self.service.project_summary_lines(),
        ]
        self.summary_view.setPlainText(join_lines(lines))
