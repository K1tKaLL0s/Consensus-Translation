from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REACT_SRC = ROOT / "UI design" / "High-Fidelity Translation Software UI" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


REQUIRED_TS_CONTRACTS = {
    "execution_mode.ts",
    "workflow_mode.ts",
    "task_status.ts",
    "learning_strategy.ts",
    "provider_health.ts",
    "capability_map.ts",
    "consensus_dto.ts",
    "error_code.ts",
    "finalize_service.ts",
}

REQUIRED_CAPABILITIES = {
    "text_translation",
    "image_translation",
    "file_translation",
    "local_mode",
    "ai_mode",
    "learning_mode",
    "self_iterative",
    "self_decision",
    "mock_provider",
    "cloud_termbase",
}

REQUIRED_MATRIX_ITEMS = {
    "text_translation",
    "image_translation_ocr",
    "file_translation",
    "local_mode",
    "ai_collaboration_mode",
    "openai_compatible_api_config",
    "provider_preflight_health_check",
    "standard_translation",
    "learning_mode",
    "human_review",
    "self_iterative",
    "self_decision",
    "history",
    "translation_detail",
    "user_rating",
    "local_termbase",
    "cloud_termbase",
    "termbase_import",
    "termbase_export",
    "consensus_conflict_arbitration",
    "vote_map_explainability",
    "settings_privacy_appearance",
}


def test_react_contract_layer_defines_required_files_and_dto_exports():
    contracts_dir = REACT_SRC / "contracts"

    assert contracts_dir.is_dir()
    assert {path.name for path in contracts_dir.glob("*.ts")} >= REQUIRED_TS_CONTRACTS

    capability_text = (contracts_dir / "capability_map.ts").read_text(encoding="utf-8")
    provider_text = (contracts_dir / "provider_health.ts").read_text(encoding="utf-8")
    consensus_text = (contracts_dir / "consensus_dto.ts").read_text(encoding="utf-8")

    for capability in REQUIRED_CAPABILITIES:
        assert capability in capability_text
    for field in (
        "status",
        "latency",
        "reliability_score",
        "fallback_chain",
        "is_mock",
        "is_production_ready",
    ):
        assert field in provider_text
    for field in (
        "final_text",
        "vote_map",
        "conflicts",
        "arbitration_reason",
        "alignment_level",
        "requires_review",
    ):
        assert field in consensus_text
    assert "semantic" not in consensus_text.lower()


def test_react_core_surfaces_use_contract_layer_instead_of_mock_capability_data():
    pages = [
        REACT_SRC / "app" / "pages" / "MainWorkspace.tsx",
        REACT_SRC / "app" / "pages" / "LearningMode.tsx",
        REACT_SRC / "app" / "pages" / "TermbaseManagement.tsx",
        REACT_SRC / "app" / "pages" / "History.tsx",
        REACT_SRC / "app" / "pages" / "TranslationDetail.tsx",
        REACT_SRC / "app" / "components" / "Sidebar.tsx",
    ]

    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert "../data/mockData" not in text
    assert "../../contracts/capability_map" in pages[0].read_text(encoding="utf-8")
    assert "../../contracts/capability_map" in pages[1].read_text(encoding="utf-8")
    assert "../../contracts/capability_map" in pages[2].read_text(encoding="utf-8")
    assert "../../contracts/task_status" in pages[0].read_text(encoding="utf-8")


def test_task_status_mapping_uses_product_state_machine():
    from consensus_translation.product_contracts import TaskStatus, map_task_status

    assert {item.value for item in TaskStatus} == {
        "idle",
        "queued",
        "running",
        "awaiting_confirmation",
        "completed",
        "failed",
        "cancelled",
    }
    assert map_task_status("running") == TaskStatus.RUNNING
    assert map_task_status("awaiting_human_confirmation") == TaskStatus.AWAITING_CONFIRMATION
    assert map_task_status("needs_review") == TaskStatus.AWAITING_CONFIRMATION
    assert map_task_status("finalized") == TaskStatus.COMPLETED
    assert map_task_status("rejected") == TaskStatus.CANCELLED
    assert map_task_status("budget_exceeded") == TaskStatus.FAILED


def test_capability_map_and_frontend_backend_matrix_cover_required_product_surface():
    from consensus_translation.services.capability_service import (
        get_capabilities,
        get_frontend_backend_capability_matrix,
    )

    capabilities = get_capabilities(allow_mock_provider=False)
    matrix = get_frontend_backend_capability_matrix(allow_mock_provider=False)

    assert set(capabilities.keys()) == REQUIRED_CAPABILITIES
    assert capabilities["self_decision"].eligibility is not None
    assert capabilities["mock_provider"].enabled is False
    assert capabilities["mock_provider"].production_status == "blocked"
    assert capabilities["cloud_termbase"].placeholder is True
    assert capabilities["cloud_termbase"].enabled is False
    assert {item.capability_id for item in matrix} >= REQUIRED_MATRIX_ITEMS
    for item in matrix:
        assert item.backend_status in {"implemented", "partial", "missing", "disabled"}
        assert item.frontend_status in {"implemented", "partial", "missing", "hidden"}
        assert item.contract_status in {"matched", "mismatched", "missing"}
        assert item.test_status in {"covered", "not_covered"}
        assert item.production_status in {"ready", "blocked"}


def test_image_translation_capability_is_not_claimed_ready_without_stable_ui_entry():
    from consensus_translation.services.capability_service import (
        get_capabilities,
        get_frontend_backend_capability_matrix,
    )

    capabilities = get_capabilities(allow_mock_provider=False)
    image_capability = capabilities["image_translation"]
    image_matrix = {
        item.capability_id: item
        for item in get_frontend_backend_capability_matrix(allow_mock_provider=False)
    }["image_translation_ocr"]

    assert image_capability.enabled is False
    assert image_capability.backend_status == "partial"
    assert image_capability.frontend_status == "partial"
    assert image_capability.production_status == "blocked"
    assert image_matrix.production_status == "blocked"


def test_self_decision_eligibility_gate_reports_safe_blockers_and_ready_state():
    from consensus_translation.services.capability_service import get_self_decision_status

    blocked = get_self_decision_status(
        training_text="",
        validation_text="",
        api_enabled=True,
        budget_limit=1.0,
        local_provider_count=1,
        cloud_provider_count=1,
    )
    ready = get_self_decision_status(
        training_text="alpha beta gamma",
        validation_text="alpha beta",
        api_enabled=True,
        budget_limit=1.0,
        local_provider_count=1,
        cloud_provider_count=1,
    )

    assert blocked.eligible is False
    assert blocked.reason == "missing_validation"
    assert blocked.risk_level == "high"
    assert blocked.requires_ai_collaboration is True
    assert blocked.requires_human_confirmation is True
    assert blocked.rollback_supported is True

    assert ready.eligible is True
    assert ready.reason == "validation_budget_available"
    assert ready.risk_level in {"low", "medium"}
    assert ready.requires_ai_collaboration is True
    assert ready.requires_human_confirmation is True
    assert ready.rollback_supported is True


def test_provider_health_separates_mock_from_production_ready_provider():
    from consensus_translation.agent_providers import EchoModelProvider, StaticModelProvider
    from consensus_translation.services.provider_health_service import provider_health_dto

    mock_health = provider_health_dto(EchoModelProvider("mock-preview"))
    production_health = provider_health_dto(
        StaticModelProvider(
            "local-real",
            "translated",
            confidence=0.8,
            provider_kind="local",
            provider_role="local_engine",
            is_mock=False,
        )
    )

    assert mock_health.is_mock is True
    assert mock_health.is_production_ready is False
    assert mock_health.status == "mock"
    assert production_health.is_mock is False
    assert production_health.is_production_ready is True
    assert production_health.status in {"ready", "degraded"}


def test_consensus_dto_uses_heuristic_alignment_and_never_semantic_certainty():
    from consensus_translation.agent_contracts import ConsensusDecision
    from consensus_translation.product_contracts import consensus_to_dto

    dto = consensus_to_dto(
        ConsensusDecision(
            final_text="翻訳",
            final_score=0.98,
            vote_map={"local-a": 1},
            mdwc_scores={"local-a": 0.98},
            conflict_points=["style_difference"],
            decision_reason="mdwc:local-a",
            confidence_level="high",
            arbitration_reason="alignment_conflicts=style_difference",
            requires_human_review=False,
        )
    )

    assert dto.final_text == "翻訳"
    assert dto.alignment_level == "heuristic"
    assert dto.requires_review is True
    assert "semantic" not in dto.alignment_level


def test_finalize_service_is_the_only_product_facing_store_commit_path():
    workflow_text = (SRC / "consensus_translation" / "agent_workflows.py").read_text(
        encoding="utf-8"
    )
    product_surface_text = "\n".join(
        [
            (SRC / "consensus_translation" / "desktop_qt" / "application_service.py").read_text(
                encoding="utf-8"
            ),
            (SRC / "consensus_translation" / "desktop_agent_app.py").read_text(
                encoding="utf-8"
            ),
            (SRC / "consensus_translation" / "agent_lexicon_migration.py").read_text(
                encoding="utf-8"
            ),
        ]
    )

    assert "commit_agent_result(" in workflow_text
    assert "record_result(" not in workflow_text
    assert "FinalizeService(" in product_surface_text
    for forbidden in (
        "history_store.add(",
        "history_store.attach_rating(",
        "record_translation_rating",
        ".skip_translation_rating(",
        "confirm_agent_run",
        "confirm_revision_event_by_id",
        "import_json_lexicon",
        "export_all_lexicon_entries",
    ):
        assert forbidden not in product_surface_text


def test_finalize_service_does_not_save_rating_without_explicit_submit_event(tmp_path):
    from consensus_translation.agent_store import AgentRunStore
    from consensus_translation.services.finalize_service import FinalizeService

    store = AgentRunStore(tmp_path / "agent.sqlite3")
    service = FinalizeService(agent_store=store)

    assert service.skip_translation_rating("missing-run") is None
    assert store.list_translation_ratings() == []
