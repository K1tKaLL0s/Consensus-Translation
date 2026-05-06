from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.pyqt_app.api_client import ApiClient


class LLMPanel(QWidget):
    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.api_client = api_client

        self.provider_combo = QComboBox(self)
        self.provider_combo.addItems(["gpt", "qwen", "kimi", "deepseek", "gemini", "watsonx"])
        self.model_input = QLineEdit(self)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.save_button = QPushButton("保存", self)
        self.delete_button = QPushButton("删除", self)
        self.refresh_button = QPushButton("刷新", self)

        self.save_button.clicked.connect(self.save_config)
        self.delete_button.clicked.connect(self.delete_config)
        self.refresh_button.clicked.connect(self.refresh_config)

        form = QFormLayout()
        form.addRow("Provider", self.provider_combo)
        form.addRow("Model", self.model_input)
        form.addRow("API Key", self.api_key_input)

        actions = QHBoxLayout()
        actions.addWidget(self.save_button)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)

    def save_config(self) -> dict[str, object]:
        return self.api_client.save_llm_config(
            provider=self.provider_combo.currentText(),
            model=self.model_input.text(),
            api_key=self.api_key_input.text(),
        )

    def delete_config(self) -> dict[str, object]:
        payload = self.api_client.delete_llm_config()
        self.api_key_input.clear()
        return payload

    def refresh_config(self) -> dict[str, object]:
        payload = self.api_client.get_llm_config()
        provider = str(payload.get("provider") or "")
        model = str(payload.get("model") or "")
        if provider:
            index = self.provider_combo.findText(provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        self.model_input.setText(model)
        if not payload.get("api_key_configured", False):
            self.api_key_input.clear()
        return payload
