from PyQt6.QtWidgets import QApplication, QPushButton, QTextEdit, QVBoxLayout, QWidget


class ResultPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.result_text = QTextEdit(self)
        self.result_text.setReadOnly(True)
        self.copy_button = QPushButton("复制", self)
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_to_clipboard)

        layout = QVBoxLayout(self)
        layout.addWidget(self.result_text)
        layout.addWidget(self.copy_button)

    def set_text(self, value: str) -> None:
        self.result_text.setPlainText(value)

    def set_copy_allowed(self, allowed: bool) -> None:
        self.copy_button.setEnabled(bool(allowed))

    def _copy_to_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_text.toPlainText())
