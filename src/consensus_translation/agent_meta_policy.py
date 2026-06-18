from __future__ import annotations

from dataclasses import dataclass

from consensus_translation.agent_context import estimate_context_tokens
from consensus_translation.agent_contracts import AgentMode


@dataclass(frozen=True)
class MetaPolicyDecision:
    selected_mode: AgentMode
    reason: str
    validation_coverage: float


class MetaPolicyAgent:
    def select_mode(
        self,
        training_text: str | None,
        validation_text: str | None,
        api_enabled: bool,
        budget_limit: float,
    ) -> MetaPolicyDecision:
        if not training_text or not validation_text:
            return MetaPolicyDecision(AgentMode.LEARNING, "missing_validation", 0.0)
        if not api_enabled:
            return MetaPolicyDecision(AgentMode.LEARNING, "api_disabled", 0.0)
        if budget_limit <= 0:
            return MetaPolicyDecision(AgentMode.LEARNING, "budget_unavailable", 0.0)

        training_tokens = estimate_context_tokens(training_text)
        validation_tokens = estimate_context_tokens(validation_text)
        coverage = 0.0
        if training_tokens > 0:
            coverage = min(validation_tokens / training_tokens, 1.0)
        if validation_tokens < 1 or coverage <= 0.25:
            return MetaPolicyDecision(
                AgentMode.LEARNING,
                "validation_coverage_low",
                coverage,
            )
        return MetaPolicyDecision(
            AgentMode.SELF_ITERATIVE,
            "validation_budget_available",
            coverage,
        )
