from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Section(QFrame):
    """Framed content section with a consistent title and body layout."""

    def __init__(
        self,
        title: str,
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("sectionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("sectionTitle")
        self.title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.title_label)

        self.description_label = QLabel(description, self)
        self.description_label.setObjectName("sectionDescription")
        self.description_label.setWordWrap(True)
        self.description_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.description_label.setVisible(bool(description))
        layout.addWidget(self.description_label)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        layout.addLayout(self.body)

    def set_title(self, title: str, description: str = "") -> None:
        self.title_label.setText(title)
        self.description_label.setText(description)
        self.description_label.setVisible(bool(description))


def page_header(title: str, description: str, parent: QWidget | None = None) -> QWidget:
    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    title_label = QLabel(title, container)
    title_label.setObjectName("pageTitle")
    title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    layout.addWidget(title_label)

    description_label = QLabel(description, container)
    description_label.setObjectName("pageDescription")
    description_label.setWordWrap(True)
    description_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    layout.addWidget(description_label)
    return container


def primary_button(text: str, parent: QWidget | None = None) -> QPushButton:
    button = QPushButton(text, parent)
    button.setObjectName("primaryButton")
    button.setCursor(Qt.PointingHandCursor)
    return button


def secondary_button(text: str, parent: QWidget | None = None) -> QPushButton:
    button = QPushButton(text, parent)
    button.setObjectName("secondaryButton")
    button.setCursor(Qt.PointingHandCursor)
    return button


def status_badge(text: str, state: str = "neutral", parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("statusBadge")
    label.setProperty("state", state)
    label.setAlignment(Qt.AlignCenter)
    return label
