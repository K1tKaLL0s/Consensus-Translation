from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_workflow_state import (
    WorkflowEvent,
    WorkflowState,
    WorkflowStateMachine,
)


def test_workflow_state_machine_allows_controlled_translation_path():
    machine = WorkflowStateMachine()

    states = [
        machine.apply(WorkflowEvent.START_TRANSLATION),
        machine.apply(WorkflowEvent.LOCAL_TRANSLATION_DONE),
        machine.apply(WorkflowEvent.CONSENSUS_DONE),
        machine.apply(WorkflowEvent.ARBITRATION_DONE),
        machine.apply(WorkflowEvent.USER_CONFIRMED),
    ]

    assert states == [
        WorkflowState.INPUT_READY,
        WorkflowState.LOCAL_TRANSLATING,
        WorkflowState.CONSENSUS_SCORING,
        WorkflowState.WAITING_HUMAN_CONFIRMATION,
        WorkflowState.COMPLETED,
    ]
    assert machine.trace_labels() == [
        "workflow:inputReady",
        "workflow:localTranslating",
        "workflow:consensusScoring",
        "workflow:waitingHumanConfirmation",
        "workflow:completed",
    ]


def test_workflow_state_machine_rejects_out_of_order_events():
    machine = WorkflowStateMachine()

    with pytest.raises(ValueError, match="invalid workflow transition"):
        machine.apply(WorkflowEvent.USER_CONFIRMED)


def test_workflow_state_machine_supports_error_retry_and_reset():
    machine = WorkflowStateMachine()
    machine.apply(WorkflowEvent.START_TRANSLATION)
    machine.apply(WorkflowEvent.ERROR_OCCURRED)

    assert machine.state == WorkflowState.FAILED

    machine.apply(WorkflowEvent.RETRY)

    assert machine.state == WorkflowState.INPUT_READY

    machine.apply(WorkflowEvent.RESET)

    assert machine.state == WorkflowState.IDLE


def test_workflow_state_machine_accepts_explicit_rating_event_without_state_change():
    machine = WorkflowStateMachine()
    machine.apply(WorkflowEvent.START_TRANSLATION)
    machine.apply(WorkflowEvent.LOCAL_TRANSLATION_DONE)
    machine.apply(WorkflowEvent.CONSENSUS_DONE)
    machine.apply(WorkflowEvent.ARBITRATION_DONE)

    state = machine.apply(WorkflowEvent.RATING_SUBMITTED)

    assert state == WorkflowState.WAITING_HUMAN_CONFIRMATION
    assert machine.history[-1] == WorkflowState.WAITING_HUMAN_CONFIRMATION
