from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import (
    DesktopApplicationService,
)


class WorkbenchPage(QWidget):
    def __init__(
        self,
        service: DesktopApplicationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("翻译工作台", self)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        form = QFormLayout()
        self.source_lang_input = QLineEdit(self.service.controller.config.source_lang, self)
        self.target_lang_input = QLineEdit(self.service.controller.config.target_lang, self)
        self.topic_input = QLineEdit(self.service.controller.config.topic, self)
        self.training_file_input = QLineEdit(self.service.controller.config.training_file, self)
        self.validation_file_input = QLineEdit(self.service.controller.config.validation_file, self)
        self.mode_input = QComboBox(self)
        self.mode_input.addItems(["learning", "self_iterative", "self_decision"])
        self.mode_input.setCurrentText(self.service.controller.config.mode)
        self.evaluator_input = QComboBox(self)
        self.evaluator_input.addItems(["deterministic", "comet"])
        self.evaluator_input.setCurrentText(self.service.controller.config.evaluator_kind)
        self.allow_training_upload_checkbox = QCheckBox("允许将训练样例发给远端 provider", self)
        self.allow_training_upload_checkbox.setChecked(
            self.service.controller.config.allow_training_upload
        )
        form.addRow("源语言", self.source_lang_input)
        form.addRow("目标语言", self.target_lang_input)
        form.addRow("题材", self.topic_input)
        form.addRow("模式", self.mode_input)
        form.addRow("评估器", self.evaluator_input)
        form.addRow("训练文件", self.training_file_input)
        form.addRow("验证文件", self.validation_file_input)
        form.addRow("", self.allow_training_upload_checkbox)
        layout.addLayout(form)

        editors = QHBoxLayout()
        self.source_editor = QPlainTextEdit(self)
        self.source_editor.setPlaceholderText("输入待翻译文本，或后续通过文件/OCR/连接器导入。")
        self.result_editor = QPlainTextEdit(self)
        self.result_editor.setReadOnly(True)
        editors.addWidget(self.source_editor)
        editors.addWidget(self.result_editor)
        layout.addLayout(editors, 1)

        self.candidates_list = QListWidget(self)
        layout.addWidget(self.candidates_list)

        self.preflight_view = QPlainTextEdit(self)
        self.preflight_view.setReadOnly(True)
        self.preflight_view.setPlaceholderText("远端调用预检、预算、确认 ID 和错误信息会显示在这里。")
        layout.addWidget(self.preflight_view)

        action_row = QHBoxLayout()
        self.open_file_button = QPushButton("载入文件", self)
        self.preview_button = QPushButton("预检远端调用", self)
        self.confirm_remote_button = QPushButton("确认远端调用", self)
        self.translate_button = QPushButton("运行翻译", self)
        self.confirm_run_button = QPushButton("确认当前任务", self)
        self.export_button = QPushButton("导出产物", self)
        self.open_file_button.clicked.connect(self.open_source_file)
        self.preview_button.clicked.connect(self.preview_remote_calls)
        self.confirm_remote_button.clicked.connect(self.confirm_remote_calls)
        self.translate_button.clicked.connect(self.translate_current_text)
        self.confirm_run_button.clicked.connect(self.confirm_current_run)
        self.export_button.clicked.connect(lambda: self.export_artifacts(None))
        self.status_label = QLabel("就绪", self)
        action_row.addWidget(self.open_file_button)
        action_row.addWidget(self.preview_button)
        action_row.addWidget(self.confirm_remote_button)
        action_row.addWidget(self.translate_button)
        action_row.addWidget(self.confirm_run_button)
        action_row.addWidget(self.export_button)
        action_row.addWidget(self.status_label, 1)
        layout.addLayout(action_row)
        self._last_run_id = ""

    def _config_kwargs(self) -> dict[str, object]:
        return {
            "source_lang": self.source_lang_input.text(),
            "target_lang": self.target_lang_input.text(),
            "topic": self.topic_input.text(),
            "mode": self.mode_input.currentText(),
            "evaluator_kind": self.evaluator_input.currentText(),
            "training_file": self.training_file_input.text(),
            "validation_file": self.validation_file_input.text(),
            "allow_training_upload": self.allow_training_upload_checkbox.isChecked(),
        }

    def open_source_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择待翻译文件",
            str(self.service.data_root),
            "Text documents (*.txt *.md *.docx);;All files (*.*)",
        )
        if path:
            self.load_source_file(path)

    def load_source_file(self, path: str | Path) -> str:
        text = self.service.load_source_file(path)
        self.source_editor.setPlainText(text)
        self.status_label.setText(f"已载入：{path}")
        return text

    def preview_remote_calls(self) -> None:
        try:
            lines = self.service.preview_remote_calls(
                self.source_editor.toPlainText(),
                **self._config_kwargs(),
            )
        except Exception as exc:
            self.preflight_view.setPlainText(str(exc))
            self.status_label.setText("预检错误")
            return
        self.preflight_view.setPlainText("\n".join(lines))
        self.status_label.setText("预检完成")

    def confirm_remote_calls(self) -> None:
        try:
            confirmation_id = self.service.confirm_remote_preflight(
                self.source_editor.toPlainText(),
                **self._config_kwargs(),
            )
        except Exception as exc:
            self.preflight_view.setPlainText(str(exc))
            self.status_label.setText("确认错误")
            return
        current = self.preflight_view.toPlainText()
        prefix = f"confirmed: {confirmation_id}"
        self.preflight_view.setPlainText(
            prefix if not current else f"{prefix}\n{current}"
        )
        self.status_label.setText("已确认远端调用")

    def translate_current_text(self) -> None:
        self.status_label.setText("运行中")
        try:
            result = self.service.translate_text(
                self.source_editor.toPlainText(),
                **self._config_kwargs(),
            )
        except Exception as exc:  # UI boundary: render recoverable controller errors.
            self.result_editor.setPlainText(str(exc))
            try:
                self.preview_remote_calls()
            except Exception:
                pass
            self.status_label.setText("错误")
            return
        self.result_editor.setPlainText(result.final_text)
        self.status_label.setText(result.status_label)
        self._last_run_id = result.run_id
        self.candidates_list.clear()
        for item in result.candidates:
            self.candidates_list.addItem(item)

    def confirm_current_run(self) -> None:
        if not self._last_run_id:
            self.status_label.setText("没有可确认任务")
            return
        if self.service.confirm_run(self._last_run_id):
            self.status_label.setText("当前任务已确认")
        else:
            self.status_label.setText("确认失败")

    def export_artifacts(self, output_dir: str | Path | None = None):
        if output_dir is None:
            selected = QFileDialog.getExistingDirectory(
                self,
                "选择导出目录",
                str(self.service.data_root),
            )
            if not selected:
                return {}
            output_dir = selected
        artifacts = self.service.export_last_translation(
            output_dir,
            base_name=self.service.controller.project_id,
        )
        self.preflight_view.setPlainText(
            "\n".join(f"{name}: {path}" for name, path in artifacts.items())
        )
        self.status_label.setText("导出完成")
        return artifacts
