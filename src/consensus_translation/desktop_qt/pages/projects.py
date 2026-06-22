from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
)


class ProjectsPage(QWidget):
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

        title = QLabel("项目与任务", self)
        title.setObjectName("pageTitle")
        self.runs_list = QListWidget(self)
        self.status_label = QLabel("就绪", self)
        self.refresh_button = QPushButton("刷新任务", self)
        self.confirm_button = QPushButton("确认选中任务", self)
        self.refresh_button.clicked.connect(self.refresh)
        self.confirm_button.clicked.connect(self.confirm_selected_run)

        buttons = QHBoxLayout()
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.confirm_button)
        buttons.addWidget(self.status_label, 1)

        layout.addWidget(title)
        layout.addWidget(self.runs_list, 1)
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        self.runs_list.clear()
        for run in self.service.list_runs():
            run_id = str(run["run_id"])
            item_text = (
                f"{run_id} | {run['status']} | score={float(run['final_score']):.2f}"
            )
            self.runs_list.addItem(item_text)
            self.runs_list.item(self.runs_list.count() - 1).setData(Qt.UserRole, run_id)
        self.status_label.setText(f"任务数：{self.runs_list.count()}")

    def confirm_selected_run(self) -> None:
        item = self.runs_list.currentItem()
        if item is None:
            self.status_label.setText("请选择任务")
            return
        run_id = str(item.data(Qt.UserRole))
        if self.service.confirm_run(run_id):
            self.status_label.setText(f"已确认：{run_id}")
        else:
            self.status_label.setText(f"未找到：{run_id}")
        self.refresh()
