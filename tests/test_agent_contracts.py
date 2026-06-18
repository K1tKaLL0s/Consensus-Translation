from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_contracts import AgentMode, policy_for_mode


def test_mode_policies_encode_three_phase3_operating_modes():
    learning = policy_for_mode(AgentMode.LEARNING, api_enabled=False, budget_limit=0.0)
    self_iterative = policy_for_mode(
        AgentMode.SELF_ITERATIVE, api_enabled=True, budget_limit=3.0
    )
    self_decision = policy_for_mode(
        AgentMode.SELF_DECISION, api_enabled=True, budget_limit=1.5
    )

    assert learning.max_rounds == 1
    assert learning.human_gate_required is True
    assert learning.validation_required is False
    assert learning.api_enabled is False

    assert self_iterative.max_rounds == 3
    assert self_iterative.human_gate_required is False
    assert self_iterative.validation_required is True
    assert self_iterative.api_enabled is True

    assert self_decision.max_rounds == 3
    assert self_decision.human_gate_required is False
    assert self_decision.validation_required is False
    assert self_decision.api_enabled is True
