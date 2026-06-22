from __future__ import annotations

from dataclasses import dataclass

from consensus_translation.agent_context import estimate_context_tokens
from consensus_translation.agent_contracts import AgentMode


@dataclass(frozen=True)
class MetaPolicyContext:
    task_text: str = ""
    topic_match_score: float = 0.0
    domain_tag_count: int = 0
    special_marker_count: int = 0
    user_correction_count: int = 0
    high_risk_term_count: int = 0
    local_provider_count: int = 0
    cloud_provider_count: int = 0
    average_candidate_confidence: float = 0.0
    topic_average_rating: float = 0.0
    language_pair_average_rating: float = 0.0
    provider_average_rating: float = 0.0
    recent_low_rating_count: int = 0
    mdwc_user_mismatch_rate: float = 0.0
    terminology_issue_ratio: float = 0.0
    style_issue_ratio: float = 0.0
    lore_issue_ratio: float = 0.0
    rating_sample_count: int = 0

    @property
    def task_tokens(self) -> int:
        return estimate_context_tokens(self.task_text)

    @property
    def risk_score(self) -> float:
        score = 0.0
        score += min(self.domain_tag_count / 3.0, 1.0) * 0.22
        score += min(self.special_marker_count / 2.0, 1.0) * 0.28
        score += min(self.user_correction_count / 3.0, 1.0) * 0.20
        score += min(self.high_risk_term_count / 2.0, 1.0) * 0.18
        if self.task_tokens >= 1200:
            score += 0.12
        elif self.task_tokens >= 400:
            score += 0.06
        if self.rating_sample_count >= 3:
            if self.topic_average_rating and self.topic_average_rating <= 2.5:
                score += 0.24
            if self.provider_average_rating and self.provider_average_rating <= 2.5:
                score += 0.20
            score += min(self.recent_low_rating_count / 4.0, 1.0) * 0.18
            score += min(self.mdwc_user_mismatch_rate, 1.0) * 0.20
            score += min(self.terminology_issue_ratio, 1.0) * 0.08
            score += min(self.style_issue_ratio, 1.0) * 0.06
            score += min(self.lore_issue_ratio, 1.0) * 0.06
        return min(score, 1.0)


@dataclass(frozen=True)
class MetaPolicyDecision:
    selected_mode: AgentMode
    reason: str
    validation_coverage: float
    risk_level: str
    requires_human_confirmation: bool
    max_iterations: int
    budget_limit: float
    fallback_plan: str

    def as_spec_payload(self) -> dict[str, object]:
        return {
            "selectedMode": _MODE_SPEC_NAMES[self.selected_mode],
            "reason": self.reason,
            "riskLevel": self.risk_level,
            "requiresHumanConfirmation": self.requires_human_confirmation,
            "maxIterations": self.max_iterations,
            "budgetLimit": self.budget_limit,
            "fallbackPlan": self.fallback_plan,
        }


_MODE_SPEC_NAMES = {
    AgentMode.LOCAL_ONLY: "localOnly",
    AgentMode.AI_ASSISTED: "aiAssisted",
    AgentMode.LEARNING: "learning",
    AgentMode.SELF_ITERATIVE: "selfIteration",
    AgentMode.SELF_DECISION: "selfDecision",
    AgentMode.PRETRAINING: "pretraining",
}

_MAX_SELF_ITERATIONS = 3
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _max_risk(left: str, right: str) -> str:
    return left if _RISK_ORDER[left] >= _RISK_ORDER[right] else right


def _decision(
    selected_mode: AgentMode,
    reason: str,
    validation_coverage: float,
    *,
    risk_level: str,
    max_iterations: int,
    budget_limit: float,
    fallback_plan: str,
) -> MetaPolicyDecision:
    return MetaPolicyDecision(
        selected_mode=selected_mode,
        reason=reason,
        validation_coverage=validation_coverage,
        risk_level=risk_level,
        requires_human_confirmation=True,
        max_iterations=min(max_iterations, _MAX_SELF_ITERATIONS),
        budget_limit=budget_limit,
        fallback_plan=fallback_plan,
    )


def _validation_coverage(training_text: str | None, validation_text: str | None) -> float:
    if not training_text or not validation_text:
        return 0.0
    training_tokens = estimate_context_tokens(training_text)
    validation_tokens = estimate_context_tokens(validation_text)
    if training_tokens <= 0:
        return 0.0
    return min(validation_tokens / training_tokens, 1.0)


def _rating_history_requires_review(context: MetaPolicyContext) -> bool:
    if context.rating_sample_count < 3:
        return False
    low_topic = bool(context.topic_average_rating and context.topic_average_rating <= 2.5)
    low_provider = bool(context.provider_average_rating and context.provider_average_rating <= 2.5)
    repeated_low = context.recent_low_rating_count >= 3
    mismatch = context.mdwc_user_mismatch_rate >= 0.6
    return low_topic or low_provider or repeated_low or mismatch


def _risk_level(context: MetaPolicyContext) -> str:
    if context.risk_score >= 0.50:
        return "high"
    if context.risk_score >= 0.20:
        return "medium"
    return "low"


class MetaPolicyAgent:
    def select_mode(
        self,
        training_text: str | None,
        validation_text: str | None,
        api_enabled: bool,
        budget_limit: float,
        context: MetaPolicyContext | None = None,
    ) -> MetaPolicyDecision:
        active_context = context or MetaPolicyContext()
        coverage = _validation_coverage(training_text, validation_text)
        risk_level = _risk_level(active_context)

        if not training_text or not validation_text:
            return _decision(
                AgentMode.LEARNING,
                "missing_validation",
                0.0,
                risk_level="high",
                max_iterations=1,
                budget_limit=budget_limit,
                fallback_plan="stay_in_learning_mode_until_validation_set_exists",
            )
        if not api_enabled:
            if active_context.local_provider_count > 0:
                return _decision(
                    AgentMode.LOCAL_ONLY,
                    "api_disabled_local_available",
                    coverage,
                    risk_level=_max_risk(risk_level, "medium"),
                    max_iterations=1,
                    budget_limit=budget_limit,
                    fallback_plan="use_local_only_without_cloud_providers",
                )
            return _decision(
                AgentMode.LEARNING,
                "api_disabled",
                coverage,
                risk_level="medium",
                max_iterations=1,
                budget_limit=budget_limit,
                fallback_plan="use_local_learning_without_cloud_providers",
            )
        if budget_limit <= 0:
            return _decision(
                AgentMode.LEARNING,
                "budget_unavailable",
                coverage,
                risk_level="medium",
                max_iterations=1,
                budget_limit=budget_limit,
                fallback_plan="stay_in_learning_mode_until_budget_is_available",
            )

        if coverage <= 0.25:
            return _decision(
                AgentMode.LEARNING,
                "validation_coverage_low",
                coverage,
                risk_level="high",
                max_iterations=1,
                budget_limit=budget_limit,
                fallback_plan="stay_in_learning_mode_until_validation_coverage_improves",
            )
        if _rating_history_requires_review(active_context):
            return _decision(
                AgentMode.LEARNING,
                "rating_history_requires_review",
                coverage,
                risk_level="high",
                max_iterations=1,
                budget_limit=budget_limit,
                fallback_plan="raise_human_confirmation_until_rating_history_recovers",
            )
        if risk_level == "high":
            return _decision(
                AgentMode.LEARNING,
                "high_risk_requires_learning_gate",
                coverage,
                risk_level="high",
                max_iterations=1,
                budget_limit=budget_limit,
                fallback_plan="stay_in_learning_mode_until_risk_is_confirmed_by_user",
            )

        return _decision(
            AgentMode.SELF_ITERATIVE,
            "validation_budget_available",
            coverage,
            risk_level=_max_risk(risk_level, "medium"),
            max_iterations=_MAX_SELF_ITERATIONS,
            budget_limit=budget_limit,
            fallback_plan="fall_back_to_learning_mode_on_validation_or_budget_failure",
        )
