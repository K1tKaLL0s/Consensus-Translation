from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from consensus_translation.desktop_qt.application_service import DesktopApplicationService
from consensus_translation.desktop_qt.components import primary_button, secondary_button, status_badge
from consensus_translation.desktop_qt.history_store import TranslationHistoryRecord
from consensus_translation.desktop_qt.i18n import I18n


class HistoryPage(QWidget):
    def __init__(
        self,
        service: DesktopApplicationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.i18n = I18n(service.load_user_settings().interface_language)
        self._records: list[TranslationHistoryRecord] = []
        self._build_ui()
        self.retranslate()
        self.refresh()

    def set_i18n(self, i18n: I18n) -> None:
        self.i18n = i18n
        self.retranslate()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        self.title_label = QLabel(self)
        self.title_label.setObjectName("pageTitle")
        self.empty_label = QLabel(self)
        self.empty_label.setObjectName("pageDescription")
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.empty_label)

        self.history_list = QListWidget(self)
        self.history_list.itemDoubleClicked.connect(lambda _item: self.use_selected())
        layout.addWidget(self.history_list, 1)

        actions = QHBoxLayout()
        self.use_selected_button = primary_button("", self)
        self.clear_button = secondary_button("", self)
        self.status_label = status_badge("", "neutral", self)
        self.use_selected_button.clicked.connect(self.use_selected)
        self.clear_button.clicked.connect(self.clear_history)
        actions.addWidget(self.use_selected_button)
        actions.addWidget(self.clear_button)
        actions.addWidget(self.status_label, 1)
        layout.addLayout(actions)

    def retranslate(self) -> None:
        self.title_label.setText(self.i18n.t("history.title"))
        self.empty_label.setText(self.i18n.t("history.empty"))
        self.history_list.setAccessibleName(self.i18n.t("history.title"))
        self.use_selected_button.setText(self.i18n.t("history.useSelected"))
        self.clear_button.setText(self.i18n.t("history.clear"))
        if not self.status_label.text():
            self.status_label.setText(self.i18n.t("translate.ready"))

    def refresh(self) -> None:
        self._records = self.service.list_translation_history()
        self.history_list.clear()
        for index, record in enumerate(self._records):
            item = QListWidgetItem(self._record_text(record))
            item.setData(Qt.UserRole, index)
            self.history_list.addItem(item)
        has_records = bool(self._records)
        self.empty_label.setVisible(not has_records)
        self.use_selected_button.setEnabled(has_records)
        self.clear_button.setEnabled(has_records)
        if not has_records:
            self.status_label.setText(self.i18n.t("history.empty"))

    def use_selected(self) -> None:
        record = self.selected_record()
        if record is None:
            return
        window = self.window()
        translate_page = window.page("translate") if hasattr(window, "page") else None
        loader = getattr(translate_page, "load_history_record", None)
        if callable(loader):
            loader(record)
        show_page = getattr(window, "show_page", None)
        if callable(show_page):
            show_page("translate")
        self.status_label.setText(self.i18n.t("history.refilled"))

    def clear_history(self) -> None:
        self.service.clear_translation_history()
        self.refresh()

    def selected_record(self) -> TranslationHistoryRecord | None:
        item = self.history_list.currentItem()
        if item is None:
            return None
        index = item.data(Qt.UserRole)
        if not isinstance(index, int):
            return None
        if index < 0 or index >= len(self._records):
            return None
        return self._records[index]

    def _record_text(self, record: TranslationHistoryRecord) -> str:
        source = record.source_text.replace("\n", " ")[:72]
        target = record.translated_text.replace("\n", " ")[:72]
        if not self._has_workflow_metadata(record):
            return self.i18n.t(
                "history.record",
                source_language=record.source_language,
                target_language=record.target_language,
                source_text=source,
                translated_text=target,
            )
        score = "-" if record.consensus_score is None else f"{record.consensus_score:.2f}"
        conflicts = ", ".join(record.conflicts) if record.conflicts else "-"
        arbitration = record.arbitration_reason or "-"
        run_id = record.run_id or "-"
        status = record.workflow_status or "-"
        rendered = self.i18n.t(
            "history.workflowRecord",
            mode=self._mode_label(record.mode),
            status=status,
            source_language=record.source_language,
            target_language=record.target_language,
            score=score,
            confidence=record.confidence_level or "-",
            run_id=run_id,
            conflicts=conflicts,
            arbitration=arbitration,
            source_text=source,
            translated_text=target,
        )
        if record.rating is None:
            return rendered
        rating_text = self.i18n.t(
            "history.rating",
            rating=record.rating,
            issue_tags=", ".join(record.rating_issue_tags) or "-",
        )
        return f"{rendered} · {rating_text}"

    @staticmethod
    def _has_workflow_metadata(record: TranslationHistoryRecord) -> bool:
        return any(
            (
                record.topic,
                record.mode,
                record.run_id,
                record.workflow_status,
                record.workflow_steps,
                record.consensus_score is not None,
                record.confidence_level,
                record.conflicts,
                record.arbitration_reason,
                record.requires_human_review,
                record.rating is not None,
            )
        )

    def _mode_label(self, mode: str) -> str:
        mode_label_keys = {
            "local": "mode.local",
            "ai_assisted": "mode.aiAssisted",
            "learning": "mode.learning",
            "self_iterative": "mode.selfIterative",
            "self_decision": "mode.selfDecision",
            "pretraining": "mode.pretraining",
        }
        key = mode_label_keys.get(mode)
        return self.i18n.t(key) if key else (mode or "-")
