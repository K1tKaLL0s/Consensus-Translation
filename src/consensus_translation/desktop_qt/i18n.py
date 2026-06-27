from __future__ import annotations

import json
import locale as system_locale
import sys
from pathlib import Path


SUPPORTED_INTERFACE_LANGUAGES: tuple[str, ...] = ("zh-CN", "en-US")

ORIGINAL_WORKFLOW_PRODUCT_I18N_KEYS: tuple[str, ...] = (
    "language.source",
    "language.target",
    "language.autoDetect",
    "language.chinese",
    "language.english",
    "language.japanese",
    "mode.local",
    "mode.aiAssisted",
    "mode.learning",
    "mode.selfIteration",
    "mode.metaDecision",
    "mode.pretraining",
    "translate.start",
    "translate.confirmFinal",
    "translate.editTranslation",
    "translate.saveCorrection",
    "workflow.currentStep",
    "workflow.localTranslation",
    "workflow.cloudTranslation",
    "workflow.crossfire",
    "workflow.consensus",
    "workflow.arbitration",
    "workflow.humanReview",
    "workflow.completed",
    "workflow.failed",
    "agent.metaPolicy",
    "agent.terminology",
    "agent.backgroundCheck",
    "agent.crossfire",
    "agent.arbitration",
    "agent.glossaryUpdate",
    "consensus.score",
    "consensus.confidence",
    "consensus.high",
    "consensus.medium",
    "consensus.low",
    "consensus.conflicts",
    "consensus.reason",
    "consensus.requiresHumanReview",
    "glossary.title",
    "glossary.suggestions",
    "glossary.confirmWrite",
    "glossary.rejectWrite",
    "glossary.specialMark",
    "glossary.uncategorized",
    "error.generic",
    "error.network",
    "error.apiMissing",
    "error.providerUnavailable",
    "error.budgetExceeded",
    "error.validationSetMissing",
    "error.lowConfidence",
    "error.iterationLimitReached",
    "common.save",
    "common.delete",
    "common.edit",
    "common.close",
)

REQUIRED_I18N_KEYS: tuple[str, ...] = (
    *ORIGINAL_WORKFLOW_PRODUCT_I18N_KEYS,
    "app.name",
    "home.title",
    "home.description",
    "home.nextTitle",
    "home.nextDescription",
    "home.startTranslation",
    "home.loadFile",
    "home.openConnectors",
    "home.currentProject",
    "home.currentProjectDescription",
    "home.recommendedWorkflow",
    "home.recommendedWorkflowDescription",
    "home.workflowSteps",
    "home.refreshProject",
    "home.summaryTitle",
    "home.summarySubtitle",
    "help.title",
    "help.description",
    "help.searchTitle",
    "help.searchDescription",
    "help.searchPlaceholder",
    "help.searchButton",
    "help.topicsTitle",
    "help.topicsDescription",
    "help.noResults",
    "nav.translate",
    "nav.projects",
    "nav.lexicon",
    "lexicon.title",
    "lexicon.description",
    "lexicon.pendingTitle",
    "lexicon.pendingDescription",
    "lexicon.exportTitle",
    "lexicon.exportDescription",
    "lexicon.confirmedTitle",
    "lexicon.confirmedDescription",
    "lexicon.confirmedEntries",
    "lexicon.searchPlaceholder",
    "lexicon.specialOnly",
    "lexicon.editTarget",
    "lexicon.editNote",
    "lexicon.editSpecial",
    "lexicon.saveEntry",
    "lexicon.entryMetadata",
    "lexicon.confirmedItem",
    "lexicon.specialFlag",
    "lexicon.normalFlag",
    "lexicon.confirmedFlag",
    "lexicon.unconfirmedFlag",
    "lexicon.selectConfirmedEntry",
    "lexicon.entrySaved",
    "lexicon.entrySaveFailed",
    "lexicon.refreshPending",
    "lexicon.confirmSelected",
    "lexicon.skipSelected",
    "lexicon.markSpecialSelected",
    "lexicon.skipped",
    "lexicon.markedSpecial",
    "lexicon.pendingStatus",
    "lexicon.selectEntry",
    "lexicon.confirmed",
    "lexicon.notFound",
    "lexicon.pendingItem",
    "projects.title",
    "projects.description",
    "projects.taskTitle",
    "projects.taskDescription",
    "projects.refresh",
    "projects.confirmSelected",
    "projects.taskCount",
    "projects.selectTask",
    "projects.confirmed",
    "projects.notFound",
    "projects.runItem",
    "projects.status.awaitingHumanConfirmation",
    "projects.status.needsReview",
    "projects.status.finalized",
    "projects.status.rejected",
    "projects.status.budgetExceeded",
    "projects.status.unknown",
    "nav.connectors",
    "connectors.title",
    "connectors.description",
    "connectors.inboxTitle",
    "connectors.inboxDescription",
    "connectors.folderPath",
    "connectors.chooseFolder",
    "connectors.readInbox",
    "connectors.previewTitle",
    "connectors.previewDescription",
    "connectors.previewPlaceholder",
    "connectors.dialogTitle",
    "connectors.captureItem",
    "connectors.capturedStatus",
    "diagnostics.title",
    "diagnostics.description",
    "diagnostics.reportTitle",
    "diagnostics.reportDescription",
    "diagnostics.reportPlaceholder",
    "diagnostics.run",
    "diagnostics.localAcceptance",
    "diagnostics.failed",
    "diagnostics.completed",
    "diagnostics.acceptanceFailed",
    "diagnostics.acceptanceCompleted",
    "nav.providers",
    "providers.title",
    "providers.description",
    "providers.formTitle",
    "providers.formDescription",
    "providers.providerId",
    "providers.baseUrl",
    "providers.model",
    "providers.apiKey",
    "providers.estimatedCost",
    "providers.enabled",
    "providers.savedTitle",
    "providers.savedDescription",
    "providers.smokeTitle",
    "providers.smokeDescription",
    "providers.save",
    "providers.loadEnabled",
    "providers.testConnection",
    "providers.saveFailed",
    "providers.saved",
    "providers.loadFailed",
    "providers.loaded",
    "providers.stateEnabled",
    "providers.stateDisabled",
    "nav.diagnostics",
    "nav.history",
    "nav.settings",
    "nav.help",
    "settings.language",
    "settings.interfaceLanguage",
    "settings.workflowDefaultsTitle",
    "settings.workflowDefaultsDescription",
    "settings.defaultSourceLanguage",
    "settings.defaultTargetLanguage",
    "settings.defaultMode",
    "settings.budgetLimit",
    "settings.allowGlossarySuggestions",
    "settings.lexiconIoTitle",
    "settings.lexiconIoDescription",
    "settings.lexiconPath",
    "settings.lexiconPathPlaceholder",
    "settings.exportLexicon",
    "settings.importLexicon",
    "settings.lexiconPathMissing",
    "settings.lexiconExported",
    "settings.lexiconImported",
    "settings.lexiconExportFailed",
    "settings.lexiconImportFailed",
    "translate.sourceLanguage",
    "translate.targetLanguage",
    "translate.autoDetect",
    "translate.inputPlaceholder",
    "translate.outputPlaceholder",
    "translate.translateButton",
    "translate.translating",
    "translate.clear",
    "translate.copy",
    "translate.copied",
    "translate.swapLanguages",
    "translate.emptyInput",
    "translate.errorGeneric",
    "translate.errorNetwork",
    "error.validationSetMissing",
    "error.validationSetMissingHint",
    "error.workflowInputsMissing",
    "error.workflowInputsMissingHint",
    "translate.characterCount",
    "translate.consensusSummary",
    "translate.reviewRequired",
    "translate.reviewOptional",
    "translate.workflowSteps",
    "translate.workflowTimeline",
    "translate.workflowTimelineEmpty",
    "translate.workflowTimelineItem",
    "workflow.step.idle",
    "workflow.step.inputReady",
    "workflow.step.localTranslating",
    "workflow.step.localReviewing",
    "workflow.step.cloudTranslating",
    "workflow.step.crossfireRunning",
    "workflow.step.consensusScoring",
    "workflow.step.arbitration",
    "workflow.step.waitingHumanConfirmation",
    "workflow.step.glossarySuggestion",
    "workflow.step.completed",
    "workflow.step.failed",
    "translate.conflicts",
    "translate.rejectRevision",
    "translate.revisionRejected",
    "translate.noRunToReject",
    "translate.confirmGlossaryWrite",
    "translate.skipGlossaryWrite",
    "translate.markSpecial",
    "translate.glossarySuggestionItem",
    "translate.glossaryWriteConfirmed",
    "translate.glossaryWriteSkipped",
    "translate.glossaryMarkedSpecial",
    "translate.noGlossarySuggestions",
    "history.title",
    "history.empty",
    "history.workflowRecord",    "common.retry",
    "common.cancel",
    "common.confirm",
)


class I18n:
    def __init__(self, locale: str = "en-US") -> None:
        self.locale = normalize_interface_language(locale)
        self._messages = load_messages(self.locale)

    def set_locale(self, locale: str) -> None:
        self.locale = normalize_interface_language(locale)
        self._messages = load_messages(self.locale)

    def t(self, key: str, **values: object) -> str:
        template = str(self._messages.get(key, key))
        if values:
            return template.format(**values)
        return template

    def language_name(self, language_code: str) -> str:
        return self.t(f"language.{language_code}")


def normalize_interface_language(locale: str | None) -> str:
    if locale in SUPPORTED_INTERFACE_LANGUAGES:
        return str(locale)
    normalized = (locale or "").lower()
    if normalized.startswith("zh") or "chinese" in normalized:
        return "zh-CN"
    return "en-US"


def default_interface_language(browser_language: str | None = None) -> str:
    if browser_language:
        return normalize_interface_language(browser_language)
    locale_name = system_locale.getlocale()[0] or ""
    return normalize_interface_language(locale_name)


def load_messages(locale: str) -> dict[str, str]:
    normalized = normalize_interface_language(locale)
    path = Path(__file__).with_name("i18n_resources") / f"{normalized}.json"
    if not path.is_file() and hasattr(sys, "_MEIPASS"):
        path = (
            Path(sys._MEIPASS)
            / "consensus_translation"
            / "desktop_qt"
            / "i18n_resources"
            / f"{normalized}.json"
        )
    return json.loads(path.read_text(encoding="utf-8-sig"))



