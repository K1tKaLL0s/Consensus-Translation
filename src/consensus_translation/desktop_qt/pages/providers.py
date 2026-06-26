from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
    join_lines,
)


class ProvidersPage(QWidget):
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

        title = QLabel("Provider 与评估器", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.provider_id_input = QLineEdit("remote-a", self)
        self.base_url_input = QLineEdit("https://api.example.test/v1", self)
        self.model_input = QLineEdit("translator", self)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.cost_input = QLineEdit("0.0", self)
        self.enabled_checkbox = QCheckBox("启用", self)
        self.enabled_checkbox.setChecked(True)
        form.addRow("Provider ID", self.provider_id_input)
        form.addRow("Base URL", self.base_url_input)
        form.addRow("Model", self.model_input)
        form.addRow("API Key", self.api_key_input)
        form.addRow("估算成本", self.cost_input)
        form.addRow("", self.enabled_checkbox)
        layout.addLayout(form)

        self.configs_list = QListWidget(self)
        self.smoke_output = QTextEdit(self)
        self.smoke_output.setReadOnly(True)
        self.status_label = QLabel("就绪", self)
        layout.addWidget(self.configs_list)
        layout.addWidget(self.smoke_output)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("保存 Provider", self)
        self.load_button = QPushButton("加载启用 Provider", self)
        self.smoke_button = QPushButton("静态冒烟", self)
        self.save_button.clicked.connect(self.save_provider)
        self.load_button.clicked.connect(self.load_enabled)
        self.smoke_button.clicked.connect(self.smoke_providers)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.load_button)
        buttons.addWidget(self.smoke_button)
        buttons.addWidget(self.status_label, 1)
        layout.addLayout(buttons)
        self.refresh()

    def save_provider(self) -> None:
        try:
            config = self.service.save_provider_settings(
                provider_id=self.provider_id_input.text(),
                base_url=self.base_url_input.text(),
                model=self.model_input.text(),
                api_key=self.api_key_input.text(),
                estimated_cost=float(self.cost_input.text() or "0"),
                enabled=self.enabled_checkbox.isChecked(),
            )
        except Exception as exc:
            self.status_label.setText(str(exc))
            return
        self.api_key_input.clear()
        self.status_label.setText(f"已保存：{config.provider_id}")
        self.refresh()

    def load_enabled(self) -> None:
        try:
            providers = self.service.load_enabled_providers()
        except Exception as exc:
            self.status_label.setText(str(exc))
            return
        self.status_label.setText(f"已加载：{len(providers)}")

    def smoke_providers(self) -> None:
        self.smoke_output.setPlainText(
            join_lines(self.service.smoke_test_providers("hello"))
        )

    def refresh(self) -> None:
        self.configs_list.clear()
        for config in self.service.list_provider_configs():
            self.configs_list.addItem(
                f"{config.provider_id} | {config.base_url} | {config.model} | enabled={config.enabled}"
            )
