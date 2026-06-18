from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
)
from consensus_translation.desktop_qt.navigation import (
    NAVIGATION_LABELS,
    NavigationList,
)
from consensus_translation.desktop_qt.pages.diagnostics import DiagnosticsPage
from consensus_translation.desktop_qt.pages.home import HomePage
from consensus_translation.desktop_qt.pages.lexicon import LexiconPage
from consensus_translation.desktop_qt.pages.projects import ProjectsPage
from consensus_translation.desktop_qt.pages.providers import ProvidersPage
from consensus_translation.desktop_qt.pages.workbench import WorkbenchPage


class PlaceholderPage(QWidget):
    page_title = ""
    page_description = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel(self.page_title)
        title.setObjectName("pageTitle")
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        description = QLabel(self.page_description)
        description.setWordWrap(True)
        description.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch(1)


class ConnectorsPage(PlaceholderPage):
    page_title = "输入连接器"
    page_description = "接入剪贴板、OCR、文件夹收件箱和第三方工具导出的文本。"


class HelpPage(PlaceholderPage):
    page_title = "帮助中心"
    page_description = "搜索快速开始、连接器、provider、运行时排障、隐私和许可说明。"


PAGE_TYPES: tuple[type[QWidget], ...] = (
    HomePage,
    WorkbenchPage,
    ProjectsPage,
    LexiconPage,
    ConnectorsPage,
    ProvidersPage,
    DiagnosticsPage,
    HelpPage,
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: object | None = None,
        data_root: str | Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.data_root = Path(data_root).resolve() if data_root else Path.cwd() / "data"
        self.service = DesktopApplicationService.from_existing(
            controller,
            data_root=self.data_root,
        )
        self.controller = self.service
        self._pages: dict[str, QWidget] = {}

        self.setWindowTitle("共识翻译 Agent")
        self.resize(1220, 760)
        self.setMinimumSize(980, 640)
        self._build_ui()

    def navigation_labels(self) -> list[str]:
        return [
            self._navigation.item(index).text()
            for index in range(self._navigation.count())
        ]

    def show_page(self, label: str) -> None:
        if label not in self._pages:
            raise ValueError(f"unknown page: {label}")
        self._navigation.setCurrentRow(NAVIGATION_LABELS.index(label))
        self._stack.setCurrentWidget(self._pages[label])
        self.statusBar().showMessage(f"当前页面：{label}")

    def page(self, label: str) -> QWidget:
        if label not in self._pages:
            raise ValueError(f"unknown page: {label}")
        return self._pages[label]

    def current_page(self) -> QWidget:
        return self._stack.currentWidget()

    def visible_text(self) -> str:
        parts: list[str] = [self.windowTitle()]
        for widget in self.findChildren(QWidget):
            if isinstance(widget, QLineEdit):
                if widget.echoMode() == QLineEdit.Normal:
                    parts.append(widget.text())
                continue
            if isinstance(widget, (QTextEdit, QPlainTextEdit)):
                parts.append(widget.toPlainText())
                continue
            if isinstance(widget, QListWidget):
                for index in range(widget.count()):
                    parts.append(widget.item(index).text())
                continue
            if isinstance(widget, QComboBox):
                parts.append(widget.currentText())
                continue
            if isinstance(widget, QCheckBox):
                parts.append(widget.text())
                continue
            if isinstance(widget, (QLabel, QPushButton)):
                parts.append(widget.text())
        return "\n".join(part for part in parts if part)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._navigation = NavigationList(self)
        self._navigation.currentRowChanged.connect(self._on_navigation_changed)
        root_layout.addWidget(self._navigation)

        content = QWidget(self)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._build_header())

        self._stack = QStackedWidget(self)
        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for label, page_type in zip(NAVIGATION_LABELS, PAGE_TYPES, strict=True):
            if issubclass(page_type, PlaceholderPage):
                page = page_type(self)
            else:
                page = page_type(self.service, self)
            self._pages[label] = page
            self._stack.addWidget(page)
        content_layout.addWidget(self._stack)

        root_layout.addWidget(content, 1)
        self.setCentralWidget(central)

        status_bar = QStatusBar(self)
        status_bar.showMessage("就绪：本地优先，远端调用需显式确认")
        self.setStatusBar(status_bar)
        self._navigation.setCurrentRow(0)

    def _build_header(self) -> QFrame:
        header = QFrame(self)
        header.setObjectName("topBar")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(16)

        title = QLabel("共识翻译 Agent", header)
        title.setObjectName("appTitle")
        subtitle = QLabel(
            f"数据目录：{self.data_root}   ·   本地优先 / 可审计 / 人工确认",
            header,
        )
        subtitle.setObjectName("appSubtitle")
        subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(title)
        layout.addWidget(subtitle, 1)
        return header

    def _on_navigation_changed(self, row: int) -> None:
        if row < 0:
            return
        self._stack.setCurrentIndex(row)
        self.statusBar().showMessage(f"当前页面：{NAVIGATION_LABELS[row]}")
