from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from consensus_translation.agent_contracts import ConsensusDecision


class ExecutionMode(StrEnum):
    LOCAL = "local"
    AI_ASSISTED = "ai_assisted"
    LEARNING = "learning"
    SELF_ITERATIVE = "self_iterative"
    SELF_DECISION = "self_decision"
    PRETRAINING = "pretraining"


class WorkflowMode(StrEnum):
    STANDARD = "standard"
    LEARNING = "learning"
    REVIEW = "review"


class TaskStatus(StrEnum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LearningStrategy(StrEnum):
    TRAINING_SET = "training_set"
    VALIDATION_SET = "validation_set"
    ROUNDS = "rounds"
    HUMAN_REVIEW = "human_review"
    SELF_ITERATIVE = "self_iterative"
    SELF_DECISION = "self_decision"


class ErrorCode(StrEnum):
    NONE = "none"
    VALIDATION_REQUIRED = "validation_required"
    HUMAN_CONFIRMATION_REQUIRED = "human_confirmation_required"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MOCK_PROVIDER_BLOCKED = "mock_provider_blocked"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    STORE_COMMIT_FAILED = "store_commit_failed"


ProviderStatus = Literal["ready", "degraded", "unavailable", "mock"]
CapabilityStatus = Literal["implemented", "partial", "missing", "disabled"]
FrontendStatus = Literal["implemented", "partial", "missing", "hidden"]
ContractStatus = Literal["matched", "mismatched", "missing"]
TestStatus = Literal["covered", "not_covered"]
ProductionStatus = Literal["ready", "blocked"]
AlignmentLevel = Literal["heuristic", "surface", "token", "none"]
RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class SelfDecisionStatusDTO:
    eligible: bool
    reason: str
    risk_level: RiskLevel
    requires_ai_collaboration: bool
    requires_human_confirmation: bool
    rollback_supported: bool


@dataclass(frozen=True)
class ProviderHealthDTO:
    status: ProviderStatus
    latency: float
    reliability_score: float
    fallback_chain: tuple[str, ...]
    is_mock: bool
    is_production_ready: bool


@dataclass(frozen=True)
class CapabilityDTO:
    id: str
    enabled: bool
    backend_status: CapabilityStatus
    frontend_status: FrontendStatus
    contract_status: ContractStatus
    test_status: TestStatus
    production_status: ProductionStatus
    reason: str = ""
    placeholder: bool = False
    eligibility: SelfDecisionStatusDTO | None = None


@dataclass(frozen=True)
class CapabilityMatrixItem:
    capability_id: str
    label: str
    backend_status: CapabilityStatus
    frontend_status: FrontendStatus
    contract_status: ContractStatus
    test_status: TestStatus
    production_status: ProductionStatus
    backend_api: str
    frontend_entry: str
    dto: str
    notes: str = ""


@dataclass(frozen=True)
class ConsensusDTO:
    final_text: str
    vote_map: dict[str, int]
    conflicts: tuple[str, ...]
    arbitration_reason: str
    alignment_level: AlignmentLevel
    requires_review: bool


@dataclass(frozen=True)
class LearningState:
    training_set: str = ""
    validation_set: str = ""
    rounds: int = 0
    human_review: bool = True
    self_iterative: bool = False
    self_decision: SelfDecisionStatusDTO | None = None


@dataclass(frozen=True)
class FinalizeEventDTO:
    event_type: str
    task_status: TaskStatus
    run_id: str = ""
    error_code: ErrorCode = ErrorCode.NONE
    metadata: dict[str, object] = field(default_factory=dict)


_TASK_STATUS_MAP = {
    "idle": TaskStatus.IDLE,
    "queued": TaskStatus.QUEUED,
    "running": TaskStatus.RUNNING,
    "awaiting_human_confirmation": TaskStatus.AWAITING_CONFIRMATION,
    "needs_review": TaskStatus.AWAITING_CONFIRMATION,
    "review": TaskStatus.AWAITING_CONFIRMATION,
    "finalized": TaskStatus.COMPLETED,
    "completed": TaskStatus.COMPLETED,
    "failed": TaskStatus.FAILED,
    "budget_exceeded": TaskStatus.FAILED,
    "rejected": TaskStatus.CANCELLED,
    "cancelled": TaskStatus.CANCELLED,
}


def map_task_status(status: str | None) -> TaskStatus:
    if status is None:
        return TaskStatus.IDLE
    return _TASK_STATUS_MAP.get(status.strip().lower(), TaskStatus.FAILED)


def consensus_to_dto(decision: ConsensusDecision) -> ConsensusDTO:
    conflicts = tuple(str(item) for item in decision.conflict_points)
    return ConsensusDTO(
        final_text=decision.final_text,
        vote_map={str(key): int(value) for key, value in decision.vote_map.items()},
        conflicts=conflicts,
        arbitration_reason=decision.arbitration_reason or decision.decision_reason,
        alignment_level="heuristic",
        requires_review=decision.requires_human_review or bool(conflicts),
    )

