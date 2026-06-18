from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class AgentMode(StrEnum):
    LEARNING = "learning"
    SELF_ITERATIVE = "self_iterative"
    SELF_DECISION = "self_decision"


class AgentRunStatus(StrEnum):
    RUNNING = "running"
    AWAITING_HUMAN_CONFIRMATION = "awaiting_human_confirmation"
    FINALIZED = "finalized"
    NEEDS_REVIEW = "needs_review"
    BUDGET_EXCEEDED = "budget_exceeded"


@dataclass(frozen=True)
class ModePolicy:
    max_rounds: int
    human_gate_required: bool
    validation_required: bool
    api_enabled: bool
    budget_limit: float


@dataclass(frozen=True)
class TranslationCandidate:
    provider_id: str
    text: str
    confidence: float
    cost: float = 0.0
    latency: float = 0.0
    term_hits: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ConsensusDecision:
    final_text: str
    final_score: float
    vote_map: dict[str, int]
    mdwc_scores: dict[str, float]
    conflict_points: list[str]
    decision_reason: str


@dataclass(frozen=True)
class LexiconUpdateProposal:
    topic: str
    layer: str
    source: str
    target: str
    rationale: str
    confidence: float
    requires_user_confirm: bool


@dataclass
class AgentRunContract:
    run_id: str
    mode: AgentMode
    input_refs: list[str]
    provider_policy: dict[str, object]
    budget: dict[str, float]
    status: AgentRunStatus = AgentRunStatus.RUNNING
    trace: list[str] = field(default_factory=list)

    @classmethod
    def new_run(
        cls,
        mode: AgentMode,
        input_refs: list[str],
        provider_ids: list[str],
        policy: ModePolicy,
    ) -> "AgentRunContract":
        return cls(
            run_id=f"agent-{uuid4().hex[:16]}",
            mode=mode,
            input_refs=input_refs,
            provider_policy={
                "providers": provider_ids,
                "api_enabled": policy.api_enabled,
                "max_rounds": policy.max_rounds,
                "human_gate_required": policy.human_gate_required,
                "validation_required": policy.validation_required,
            },
            budget={"limit": policy.budget_limit, "spent": 0.0},
        )


@dataclass(frozen=True)
class AgentRunResult:
    contract: AgentRunContract
    candidates: list[TranslationCandidate]
    decision: ConsensusDecision
    lexicon_proposals: list[LexiconUpdateProposal]


def policy_for_mode(
    mode: AgentMode | str,
    api_enabled: bool,
    budget_limit: float,
) -> ModePolicy:
    normalized = AgentMode(mode)
    if normalized == AgentMode.LEARNING:
        return ModePolicy(
            max_rounds=1,
            human_gate_required=True,
            validation_required=False,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
        )
    if normalized == AgentMode.SELF_ITERATIVE:
        return ModePolicy(
            max_rounds=3,
            human_gate_required=False,
            validation_required=True,
            api_enabled=api_enabled,
            budget_limit=budget_limit,
        )
    return ModePolicy(
        max_rounds=3,
        human_gate_required=False,
        validation_required=False,
        api_enabled=api_enabled,
        budget_limit=budget_limit,
    )
