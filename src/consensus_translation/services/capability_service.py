from __future__ import annotations

from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_meta_policy import MetaPolicyAgent, MetaPolicyContext
from consensus_translation.product_contracts import (
    CapabilityDTO,
    CapabilityMatrixItem,
    SelfDecisionStatusDTO,
)


def get_self_decision_status(
    *,
    training_text: str | None = None,
    validation_text: str | None = None,
    api_enabled: bool = False,
    budget_limit: float = 0.0,
    local_provider_count: int = 0,
    cloud_provider_count: int = 0,
    rating_sample_count: int = 0,
    recent_low_rating_count: int = 0,
    mdwc_user_mismatch_rate: float = 0.0,
    special_marker_count: int = 0,
    user_correction_count: int = 0,
) -> SelfDecisionStatusDTO:
    context = MetaPolicyContext(
        local_provider_count=local_provider_count,
        cloud_provider_count=cloud_provider_count,
        rating_sample_count=rating_sample_count,
        recent_low_rating_count=recent_low_rating_count,
        mdwc_user_mismatch_rate=mdwc_user_mismatch_rate,
        special_marker_count=special_marker_count,
        user_correction_count=user_correction_count,
    )
    decision = MetaPolicyAgent().select_mode(
        training_text=training_text,
        validation_text=validation_text,
        api_enabled=api_enabled,
        budget_limit=budget_limit,
        context=context,
    )
    eligible = (
        decision.selected_mode == AgentMode.SELF_ITERATIVE
        and decision.reason == "validation_budget_available"
    )
    return SelfDecisionStatusDTO(
        eligible=eligible,
        reason=decision.reason,
        risk_level=decision.risk_level,  # type: ignore[arg-type]
        requires_ai_collaboration=bool(api_enabled and cloud_provider_count > 0),
        requires_human_confirmation=decision.requires_human_confirmation,
        rollback_supported=True,
    )


def get_capabilities(
    *,
    allow_mock_provider: bool = False,
    self_decision_status: SelfDecisionStatusDTO | None = None,
) -> dict[str, CapabilityDTO]:
    status = self_decision_status or get_self_decision_status()
    mock_enabled = bool(allow_mock_provider)
    return {
        "text_translation": CapabilityDTO(
            id="text_translation",
            enabled=True,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready",
            reason="Agent workflow and local workflow expose text translation.",
        ),
        "image_translation": CapabilityDTO(
            id="image_translation",
            enabled=False,
            backend_status="partial",
            frontend_status="partial",
            contract_status="matched",
            test_status="covered",
            production_status="blocked",
            reason=(
                "OCR is available as a partial connector/runtime path, but the stable "
                "Windows image-translation UI is not production-ready."
            ),
        ),
        "file_translation": CapabilityDTO(
            id="file_translation",
            enabled=True,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready",
            reason="File loading uses the agent input pipeline and text workflow.",
        ),
        "local_mode": CapabilityDTO(
            id="local_mode",
            enabled=True,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready",
        ),
        "ai_mode": CapabilityDTO(
            id="ai_mode",
            enabled=True,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready",
            reason="OpenAI-compatible providers require preflight confirmation.",
        ),
        "learning_mode": CapabilityDTO(
            id="learning_mode",
            enabled=True,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready",
        ),
        "self_iterative": CapabilityDTO(
            id="self_iterative",
            enabled=True,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready",
            reason="Validation-gated iterative mode is capped at three rounds.",
        ),
        "self_decision": CapabilityDTO(
            id="self_decision",
            enabled=status.eligible,
            backend_status="implemented",
            frontend_status="implemented",
            contract_status="matched",
            test_status="covered",
            production_status="ready" if status.eligible else "blocked",
            reason=status.reason,
            eligibility=status,
        ),
        "mock_provider": CapabilityDTO(
            id="mock_provider",
            enabled=mock_enabled,
            backend_status="implemented",
            frontend_status="hidden" if not mock_enabled else "implemented",
            contract_status="matched",
            test_status="covered",
            production_status="blocked" if not mock_enabled else "ready",
            reason=(
                "Mock providers are disabled for production runs."
                if not mock_enabled
                else "Mock provider mode is explicitly allowed for tests."
            ),
        ),
        "cloud_termbase": CapabilityDTO(
            id="cloud_termbase",
            enabled=False,
            backend_status="disabled",
            frontend_status="hidden",
            contract_status="matched",
            test_status="covered",
            production_status="blocked",
            reason="Placeholder only; local termbase remains the active production path.",
            placeholder=True,
        ),
    }


def get_frontend_backend_capability_matrix(
    *,
    allow_mock_provider: bool = False,
) -> list[CapabilityMatrixItem]:
    capabilities = get_capabilities(allow_mock_provider=allow_mock_provider)

    def row(
        capability_id: str,
        label: str,
        backend_api: str,
        frontend_entry: str,
        dto: str,
        *,
        notes: str = "",
        source_capability: str | None = None,
    ) -> CapabilityMatrixItem:
        capability = capabilities[source_capability or capability_id]
        return CapabilityMatrixItem(
            capability_id=capability_id,
            label=label,
            backend_status=capability.backend_status,
            frontend_status=capability.frontend_status,
            contract_status=capability.contract_status,
            test_status=capability.test_status,
            production_status=capability.production_status,
            backend_api=backend_api,
            frontend_entry=frontend_entry,
            dto=dto,
            notes=notes or capability.reason,
        )

    return [
        row(
            "text_translation",
            "文本翻译",
            "DesktopApplicationService.translate_text",
            "WorkbenchPage.translate_button",
            "ConsensusDTO / TaskStatus",
        ),
        row(
            "image_translation_ocr",
            "图片翻译/OCR",
            "DesktopAgentController.capture_plugin_input('ocr-image')",
            "Input connectors / OCR image entry",
            "CapabilityDTO",
            source_capability="image_translation",
        ),
        row(
            "file_translation",
            "文件翻译",
            "DesktopApplicationService.load_source_file",
            "WorkbenchPage.open_file_button",
            "TaskStatus",
        ),
        row(
            "local_mode",
            "本地模式",
            "run_agent_translation(mode='local')",
            "SettingsPage.default_mode_select",
            "ExecutionMode",
        ),
        row(
            "ai_collaboration_mode",
            "AI 协作模式",
            "DesktopApplicationService.preview_remote_calls",
            "WorkbenchPage.preview_button",
            "ProviderHealthDTO",
            source_capability="ai_mode",
        ),
        row(
            "openai_compatible_api_config",
            "OpenAI-compatible API 配置",
            "DesktopApplicationService.save_provider_settings",
            "ProvidersPage.save_button",
            "ProviderHealthDTO",
            source_capability="ai_mode",
        ),
        row(
            "provider_preflight_health_check",
            "provider preflight / health check",
            "DesktopApplicationService.smoke_test_providers",
            "ProvidersPage.smoke_button",
            "ProviderHealthDTO",
            source_capability="ai_mode",
        ),
        row(
            "standard_translation",
            "标准翻译",
            "DesktopApplicationService.translate_text",
            "WorkbenchPage.translate_button",
            "WorkflowMode",
            source_capability="text_translation",
        ),
        row(
            "learning_mode",
            "学习模式",
            "run_agent_translation(mode='learning')",
            "WorkbenchPage.mode_input",
            "LearningState",
        ),
        row(
            "human_review",
            "人工核验",
            "FinalizeService.confirm_run",
            "WorkbenchPage.confirm_run_button",
            "FinalizeEventDTO",
            source_capability="learning_mode",
        ),
        row(
            "self_iterative",
            "自迭代",
            "run_agent_translation(mode='self_iterative')",
            "WorkbenchPage.mode_input",
            "LearningState",
        ),
        row(
            "self_decision",
            "自决策",
            "get_self_decision_status",
            "WorkbenchPage.mode_input",
            "SelfDecisionStatusDTO",
        ),
        row(
            "history",
            "历史记录",
            "FinalizeService.commit_translation_history",
            "HistoryPage",
            "FinalizeEventDTO",
            source_capability="text_translation",
        ),
        row(
            "translation_detail",
            "翻译详情",
            "AgentRunStore.list_agent_runs",
            "ProjectsPage / HistoryPage",
            "ConsensusDTO",
            source_capability="text_translation",
        ),
        row(
            "user_rating",
            "用户评分",
            "FinalizeService.submit_rating",
            "Workbench rating controls",
            "FinalizeEventDTO",
            source_capability="learning_mode",
        ),
        row(
            "local_termbase",
            "本地词库",
            "DesktopApplicationService.export_current_topic_lexicon",
            "LexiconPage",
            "CapabilityDTO",
            source_capability="learning_mode",
        ),
        row(
            "cloud_termbase",
            "云端词库 placeholder",
            "get_capabilities",
            "hidden by cloud_termbase capability",
            "CapabilityDTO",
        ),
        row(
            "termbase_import",
            "词库导入",
            "FinalizeService.import_lexicon_from_file",
            "SettingsPage.import_lexicon_button",
            "FinalizeEventDTO",
            source_capability="learning_mode",
        ),
        row(
            "termbase_export",
            "词库导出",
            "FinalizeService.export_lexicon_to_file",
            "SettingsPage.export_lexicon_button",
            "FinalizeEventDTO",
            source_capability="learning_mode",
        ),
        row(
            "consensus_conflict_arbitration",
            "共识 / 分歧 / 裁决展示",
            "consensus_to_dto",
            "HistoryPage / ProjectsPage",
            "ConsensusDTO",
            source_capability="text_translation",
        ),
        row(
            "vote_map_explainability",
            "vote_map / explainability",
            "consensus_to_dto",
            "HistoryPage / ProjectsPage",
            "ConsensusDTO",
            source_capability="text_translation",
        ),
        row(
            "settings_privacy_appearance",
            "设置 / 隐私 / 外观",
            "UserSettingsStore",
            "SettingsPage / AppearanceSettings",
            "CapabilityDTO",
            source_capability="text_translation",
        ),
    ]
