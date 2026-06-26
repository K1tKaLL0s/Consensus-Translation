from __future__ import annotations

from consensus_translation.agent_contracts import AgentRunContract, AgentRunStatus


FINALIZED_AGENT_RUN_STATUS = AgentRunStatus.FINALIZED.value
FINALIZABLE_AGENT_RUN_STATUSES = (
    AgentRunStatus.AWAITING_HUMAN_CONFIRMATION.value,
    AgentRunStatus.NEEDS_REVIEW.value,
)


def finalize_agent_contract(
    contract: AgentRunContract,
    *,
    trace_label: str = "finalize:completed",
) -> None:
    contract.status = AgentRunStatus.FINALIZED
    if trace_label and (not contract.trace or contract.trace[-1] != trace_label):
        contract.trace.append(trace_label)


def finalized_agent_run_status() -> str:
    return FINALIZED_AGENT_RUN_STATUS


def finalizable_agent_run_statuses() -> tuple[str, ...]:
    return FINALIZABLE_AGENT_RUN_STATUSES
