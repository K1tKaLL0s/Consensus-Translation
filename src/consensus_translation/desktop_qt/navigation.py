from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget


NAVIGATION_LABELS: tuple[str, ...] = (
    "首页",
    "React 工作区",
    "翻译工作台",
    "项目与任务",
    "词库与风格",
    "输入连接器",
    "Provider 与评估器",
    "诊断与运行时",
    "历史",
    "设置",
    "帮助中心",
)


class NavigationList(QListWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideNavigation")
        self.setFixedWidth(208)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSpacing(2)
        for label in NAVIGATION_LABELS:
            item = QListWidgetItem(label)
            item.setSizeHint(item.sizeHint().expandedTo(self.gridSize()))
            self.addItem(item)
