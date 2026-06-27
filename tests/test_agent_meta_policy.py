from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_meta_policy import MetaPolicyAgent, MetaPolicyContext


def test_meta_policy_self_iteration_decision_exposes_controlled_output_contract():
    decision = MetaPolicyAgent().select_mode(
        training_text="alpha beta",
        validation_text="one two",
        api_enabled=True,
        budget_limit=2.5,
    )

    assert decision.selected_mode == AgentMode.SELF_ITERATIVE
    assert decision.reason == "validation_budget_available"
    assert decision.validation_coverage == 1.0
    assert decision.risk_level == "medium"
    assert decision.requires_human_confirmation is True
    assert decision.max_iterations == 3
    assert decision.budget_limit == 2.5
    assert (
        decision.fallback_plan
        == "fall_back_to_learning_mode_on_validation_or_budget_failure"
    )
    assert decision.as_spec_payload() == {
        "selectedMode": "selfIteration",
        "reason": "validation_budget_available",
        "riskLevel": "medium",
        "requiresHumanConfirmation": True,
        "maxIterations": 3,
        "budgetLimit": 2.5,
        "fallbackPlan": "fall_back_to_learning_mode_on_validation_or_budget_failure",
    }


def test_meta_policy_missing_validation_requires_learning_and_human_gate():
    decision = MetaPolicyAgent().select_mode(
        training_text="alpha beta",
        validation_text=None,
        api_enabled=True,
        budget_limit=2.5,
    )

    assert decision.selected_mode == AgentMode.LEARNING
    assert decision.reason == "missing_validation"
    assert decision.risk_level == "high"
    assert decision.requires_human_confirmation is True
    assert decision.max_iterations == 1
    assert decision.budget_limit == 2.5
    assert decision.fallback_plan == "stay_in_learning_mode_until_validation_set_exists"

def test_meta_policy_downgrades_to_local_only_when_api_is_disabled_but_local_is_available():
    decision = MetaPolicyAgent().select_mode(
        training_text="alpha beta",
        validation_text="one two",
        api_enabled=False,
        budget_limit=2.5,
        context=MetaPolicyContext(local_provider_count=2, cloud_provider_count=0),
    )

    assert decision.selected_mode == AgentMode.LOCAL_ONLY
    assert decision.reason == "api_disabled_local_available"
    assert decision.risk_level == "medium"
    assert decision.max_iterations == 1
    assert decision.fallback_plan == "use_local_only_without_cloud_providers"


def test_meta_policy_high_domain_and_special_risk_stays_in_learning_mode():
    decision = MetaPolicyAgent().select_mode(
        training_text="alpha beta gamma delta",
        validation_text="one two three four",
        api_enabled=True,
        budget_limit=5.0,
        context=MetaPolicyContext(
            task_text="dragon dynasty physics Leviathan archive",
            topic_match_score=1.0,
            domain_tag_count=3,
            special_marker_count=2,
            user_correction_count=3,
            high_risk_term_count=1,
            local_provider_count=2,
            cloud_provider_count=2,
        ),
    )

    assert decision.selected_mode == AgentMode.LEARNING
    assert decision.reason == "high_risk_requires_learning_gate"
    assert decision.risk_level == "high"
    assert decision.requires_human_confirmation is True
    assert decision.max_iterations == 1
    assert decision.as_spec_payload()["selectedMode"] == "learning"



def test_meta_policy_uses_rating_history_to_raise_human_gate():
    decision = MetaPolicyAgent().select_mode(
        training_text="alpha beta gamma delta",
        validation_text="one two three four",
        api_enabled=True,
        budget_limit=5.0,
        context=MetaPolicyContext(
            topic_average_rating=2.1,
            language_pair_average_rating=2.4,
            provider_average_rating=2.0,
            recent_low_rating_count=4,
            mdwc_user_mismatch_rate=0.75,
            rating_sample_count=8,
        ),
    )

    assert decision.selected_mode == AgentMode.LEARNING
    assert decision.reason == "rating_history_requires_review"
    assert decision.risk_level == "high"
    assert decision.requires_human_confirmation is True
