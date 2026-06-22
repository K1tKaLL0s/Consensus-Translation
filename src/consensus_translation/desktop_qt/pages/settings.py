from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from consensus_translation.desktop_qt.application_service import DesktopApplicationService
from consensus_translation.desktop_qt.components import Section, primary_button, secondary_button, status_badge
from consensus_translation.desktop_qt.i18n import I18n, SUPPORTED_INTERFACE_LANGUAGES
from consensus_translation.desktop_qt.settings_store import CONTROLLED_WORKFLOW_MODES
from consensus_translation.services.translation.types import (
    SUPPORTED_TRANSLATION_LANGUAGES,
    TARGET_TRANSLATION_LANGUAGES,
)


class SettingsPage(QWidget):
    def __init__(
        self,
        service: DesktopApplicationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.i18n = I18n(service.load_user_settings().interface_language)
        self._updating = False
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
        layout.addWidget(self.title_label)

        self.language_section = Section("", "", self)
        form = QFormLayout()
        self.interface_language_select = QComboBox(self)
        for locale in SUPPORTED_INTERFACE_LANGUAGES:
            self.interface_language_select.addItem(locale, locale)
        self.interface_language_select.currentIndexChanged.connect(self.save)
        self.auto_save_history_checkbox = QCheckBox(self)
        self.auto_save_history_checkbox.stateChanged.connect(self.save)
        form.addRow(self.interface_language_select)
        form.addRow(self.auto_save_history_checkbox)
        self.language_section.body.addLayout(form)
        layout.addWidget(self.language_section)

        self.workflow_section = Section("", "", self)
        workflow_form = QFormLayout()
        self.default_source_language_label = QLabel(self)
        self.default_source_language_select = QComboBox(self)
        self.default_source_language_select.currentIndexChanged.connect(self.save)
        self.default_target_language_label = QLabel(self)
        self.default_target_language_select = QComboBox(self)
        self.default_target_language_select.currentIndexChanged.connect(self.save)
        self.default_mode_label = QLabel(self)
        self.default_mode_select = QComboBox(self)
        self.default_mode_select.currentIndexChanged.connect(self.save)
        self.budget_limit_label = QLabel(self)
        self.budget_limit_input = QDoubleSpinBox(self)
        self.budget_limit_input.setRange(0.0, 999999.0)
        self.budget_limit_input.setDecimals(2)
        self.budget_limit_input.setSingleStep(0.25)
        self.budget_limit_input.valueChanged.connect(self.save)
        self.allow_glossary_suggestions_checkbox = QCheckBox(self)
        self.allow_glossary_suggestions_checkbox.stateChanged.connect(self.save)
        workflow_form.addRow(
            self.default_source_language_label,
            self.default_source_language_select,
        )
        workflow_form.addRow(
            self.default_target_language_label,
            self.default_target_language_select,
        )
        workflow_form.addRow(self.default_mode_label, self.default_mode_select)
        workflow_form.addRow(self.budget_limit_label, self.budget_limit_input)
        workflow_form.addRow(self.allow_glossary_suggestions_checkbox)
        self.workflow_section.body.addLayout(workflow_form)
        layout.addWidget(self.workflow_section)

        self.lexicon_section = Section("", "", self)
        self.lexicon_path_input = QLineEdit(self)
        self.export_lexicon_button = secondary_button("", self)
        self.import_lexicon_button = secondary_button("", self)
        self.export_lexicon_button.clicked.connect(self.export_lexicon)
        self.import_lexicon_button.clicked.connect(self.import_lexicon)
        lexicon_actions = QHBoxLayout()
        lexicon_actions.addWidget(self.lexicon_path_input, 1)
        lexicon_actions.addWidget(self.export_lexicon_button)
        lexicon_actions.addWidget(self.import_lexicon_button)
        self.lexicon_section.body.addLayout(lexicon_actions)
        layout.addWidget(self.lexicon_section)

        self.product_section = Section("", "", self)
        self.product_info_label = QLabel(self)
        self.product_info_label.setWordWrap(True)
        self.product_section.body.addWidget(self.product_info_label)
        layout.addWidget(self.product_section)

        actions = QHBoxLayout()
        self.save_button = primary_button("", self)
        self.clear_history_button = secondary_button("", self)
        self.status_label = status_badge("", "neutral", self)
        self.save_button.clicked.connect(self.save)
        self.clear_history_button.clicked.connect(self.clear_history)
        actions.addWidget(self.save_button)
        actions.addWidget(self.clear_history_button)
        actions.addWidget(self.status_label, 1)
        layout.addLayout(actions)
        layout.addStretch(1)

    def retranslate(self) -> None:
        source_value = self.default_source_language_select.currentData() or "auto"
        target_value = self.default_target_language_select.currentData() or "ja"
        mode_value = self.default_mode_select.currentData() or "local"

        self.title_label.setText(self.i18n.t("nav.settings"))
        self.language_section.set_title(self.i18n.t("settings.interfaceLanguage"))
        self.workflow_section.set_title(
            self.i18n.t("settings.workflowDefaultsTitle"),
            self.i18n.t("settings.workflowDefaultsDescription"),
        )
        self.default_source_language_label.setText(
            self.i18n.t("settings.defaultSourceLanguage")
        )
        self.default_target_language_label.setText(
            self.i18n.t("settings.defaultTargetLanguage")
        )
        self.default_mode_label.setText(self.i18n.t("settings.defaultMode"))
        self.budget_limit_label.setText(self.i18n.t("settings.budgetLimit"))
        self._populate_language_combo(
            self.default_source_language_select,
            SUPPORTED_TRANSLATION_LANGUAGES,
            str(source_value),
        )
        self._populate_language_combo(
            self.default_target_language_select,
            TARGET_TRANSLATION_LANGUAGES,
            str(target_value if target_value != "auto" else "ja"),
        )
        self._populate_mode_combo(str(mode_value))
        self.lexicon_section.set_title(
            self.i18n.t("settings.lexiconIoTitle"),
            self.i18n.t("settings.lexiconIoDescription"),
        )
        self.product_section.set_title(self.i18n.t("settings.productInfo"))
        self.interface_language_select.setAccessibleName(
            self.i18n.t("a11y.interfaceLanguage")
        )
        self.default_source_language_select.setAccessibleName(
            self.i18n.t("settings.defaultSourceLanguage")
        )
        self.default_target_language_select.setAccessibleName(
            self.i18n.t("settings.defaultTargetLanguage")
        )
        self.default_mode_select.setAccessibleName(self.i18n.t("settings.defaultMode"))
        self.budget_limit_input.setAccessibleName(self.i18n.t("settings.budgetLimit"))
        self.lexicon_path_input.setAccessibleName(self.i18n.t("settings.lexiconPath"))
        self.lexicon_path_input.setPlaceholderText(
            self.i18n.t("settings.lexiconPathPlaceholder")
        )
        self.auto_save_history_checkbox.setText(self.i18n.t("settings.autoSaveHistory"))
        self.allow_glossary_suggestions_checkbox.setText(
            self.i18n.t("settings.allowGlossarySuggestions")
        )
        self.product_info_label.setText(self.i18n.t("settings.versionPlaceholder"))
        self.export_lexicon_button.setText(self.i18n.t("settings.exportLexicon"))
        self.import_lexicon_button.setText(self.i18n.t("settings.importLexicon"))
        self.save_button.setText(self.i18n.t("common.confirm"))
        self.clear_history_button.setText(self.i18n.t("settings.clearHistory"))
        if not self.status_label.text():
            self.status_label.setText(self.i18n.t("translate.ready"))

    def refresh(self) -> None:
        settings = self.service.load_user_settings()
        self._updating = True
        self._set_combo_by_data(self.interface_language_select, settings.interface_language)
        self.auto_save_history_checkbox.setChecked(settings.auto_save_history)
        self._set_combo_by_data(
            self.default_source_language_select,
            settings.default_source_language,
        )
        self._set_combo_by_data(
            self.default_target_language_select,
            settings.default_target_language,
        )
        self._set_combo_by_data(self.default_mode_select, settings.default_mode)
        self.budget_limit_input.setValue(settings.budget_limit)
        self.allow_glossary_suggestions_checkbox.setChecked(
            settings.allow_glossary_suggestions
        )
        self._updating = False

    def save(self, *_args: object) -> None:
        if self._updating:
            return
        current = self.service.load_user_settings()
        locale = str(self.interface_language_select.currentData() or current.interface_language)
        updated = current.with_changes(
            interface_language=locale,
            auto_save_history=self.auto_save_history_checkbox.isChecked(),
            default_source_language=str(
                self.default_source_language_select.currentData()
                or current.default_source_language
            ),
            default_target_language=str(
                self.default_target_language_select.currentData()
                or current.default_target_language
            ),
            default_mode=str(self.default_mode_select.currentData() or current.default_mode),
            budget_limit=self.budget_limit_input.value(),
            allow_glossary_suggestions=(
                self.allow_glossary_suggestions_checkbox.isChecked()
            ),
        )
        self.service.save_user_settings(updated)
        window = self.window()
        set_language = getattr(window, "set_interface_language", None)
        if callable(set_language):
            set_language(locale)
        self.status_label.setText(self.i18n.t("settings.saved"))

    def clear_history(self) -> None:
        self.service.clear_translation_history()
        self.status_label.setText(self.i18n.t("history.empty"))

    def _lexicon_path(self) -> str:
        return self.lexicon_path_input.text().strip()

    def export_lexicon(self) -> None:
        path = self._lexicon_path()
        if not path:
            self.status_label.setText(self.i18n.t("settings.lexiconPathMissing"))
            return
        try:
            exported_path = self.service.export_lexicon_to_file(path)
        except Exception as exc:  # noqa: BLE001 - UI boundary converts to status text.
            self.status_label.setText(
                self.i18n.t("settings.lexiconExportFailed", message=str(exc))
            )
            return
        self.status_label.setText(
            self.i18n.t("settings.lexiconExported", path=exported_path)
        )

    def import_lexicon(self) -> None:
        path = self._lexicon_path()
        if not path:
            self.status_label.setText(self.i18n.t("settings.lexiconPathMissing"))
            return
        try:
            counts = self.service.import_lexicon_from_file(path)
        except Exception as exc:  # noqa: BLE001 - UI boundary converts to status text.
            self.status_label.setText(
                self.i18n.t("settings.lexiconImportFailed", message=str(exc))
            )
            return
        self.status_label.setText(
            self.i18n.t(
                "settings.lexiconImported",
                terms=counts.get("terms", 0),
                phrases=counts.get("phrases", 0),
                style_rules=counts.get("style_rules", 0),
            )
        )

    def _populate_language_combo(
        self,
        combo: QComboBox,
        language_codes: tuple[str, ...],
        current_value: str,
    ) -> None:
        combo.blockSignals(True)
        combo.clear()
        for code in language_codes:
            combo.addItem(self.i18n.language_name(code), code)
        self._set_combo_by_data(combo, current_value)
        combo.blockSignals(False)

    def _populate_mode_combo(self, current_value: str) -> None:
        mode_label_keys = {
            "local": "mode.local",
            "ai_assisted": "mode.aiAssisted",
            "learning": "mode.learning",
            "self_iterative": "mode.selfIterative",
            "self_decision": "mode.selfDecision",
            "pretraining": "mode.pretraining",
        }
        self.default_mode_select.blockSignals(True)
        self.default_mode_select.clear()
        for mode in CONTROLLED_WORKFLOW_MODES:
            self.default_mode_select.addItem(self.i18n.t(mode_label_keys[mode]), mode)
        self._set_combo_by_data(self.default_mode_select, current_value)
        self.default_mode_select.blockSignals(False)

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
        if combo.count():
            combo.setCurrentIndex(0)