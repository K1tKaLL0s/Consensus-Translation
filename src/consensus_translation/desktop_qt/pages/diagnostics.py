from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
    join_lines,
)


class DiagnosticsPage(QWidget):
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

        title = QLabel("诊断与运行时", self)
        title.setObjectName("pageTitle")
        self.report_view = QTextEdit(self)
        self.report_view.setReadOnly(True)
        self.status_label = QLabel("就绪", self)
        self.run_button = QPushButton("运行诊断", self)
        self.smoke_button = QPushButton("本地冒烟", self)
        self.run_button.clicked.connect(self.run_diagnostics)
        self.smoke_button.clicked.connect(self.run_local_smoke)

        buttons = QHBoxLayout()
        buttons.addWidget(self.run_button)
        buttons.addWidget(self.smoke_button)
        buttons.addWidget(self.status_label, 1)

        layout.addWidget(title)
        layout.addWidget(self.report_view, 1)
        layout.addLayout(buttons)

    def run_diagnostics(self) -> None:
        try:
            lines = self.service.run_diagnostics()
        except Exception as exc:
            self.report_view.setPlainText(str(exc))
            self.status_label.setText("错误")
            return
        self.report_view.setPlainText(join_lines(lines))
        self.status_label.setText("诊断完成")

    def run_local_smoke(self) -> None:
        try:
            lines = self.service.run_local_acceptance()
        except Exception as exc:
            self.report_view.setPlainText(str(exc))
            self.status_label.setText("错误")
            return
        self.report_view.setPlainText(join_lines(lines))
        self.status_label.setText("冒烟完成")
