from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class WorkflowState(StrEnum):
    IDLE = "idle"
    INPUT_READY = "inputReady"
    LOCAL_TRANSLATING = "localTranslating"
    LOCAL_REVIEWING = "localReviewing"
    CLOUD_TRANSLATING = "cloudTranslating"
    CROSSFIRE_RUNNING = "crossfireRunning"
    CONSENSUS_SCORING = "consensusScoring"
    ARBITRATION = "arbitration"
    WAITING_HUMAN_CONFIRMATION = "waitingHumanConfirmation"
    GLOSSARY_SUGGESTION = "glossarySuggestion"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowEvent(StrEnum):
    START_TRANSLATION = "START_TRANSLATION"
    LOCAL_TRANSLATION_DONE = "LOCAL_TRANSLATION_DONE"
    CLOUD_TRANSLATION_DONE = "CLOUD_TRANSLATION_DONE"
    CROSSFIRE_DONE = "CROSSFIRE_DONE"
    CONSENSUS_DONE = "CONSENSUS_DONE"
    ARBITRATION_DONE = "ARBITRATION_DONE"
    USER_CONFIRMED = "USER_CONFIRMED"
    USER_EDITED = "USER_EDITED"
    USER_REJECTED = "USER_REJECTED"
    GLOSSARY_CONFIRMED = "GLOSSARY_CONFIRMED"
    GLOSSARY_SKIPPED = "GLOSSARY_SKIPPED"
    RATING_SUBMITTED = "RATING_SUBMITTED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    RETRY = "RETRY"
    RESET = "RESET"


_TRANSITIONS: dict[tuple[WorkflowState, WorkflowEvent], WorkflowState] = {
    (WorkflowState.IDLE, WorkflowEvent.START_TRANSLATION): WorkflowState.INPUT_READY,
    (
        WorkflowState.INPUT_READY,
        WorkflowEvent.LOCAL_TRANSLATION_DONE,
    ): WorkflowState.LOCAL_TRANSLATING,
    (
        WorkflowState.LOCAL_TRANSLATING,
        WorkflowEvent.LOCAL_TRANSLATION_DONE,
    ): WorkflowState.LOCAL_REVIEWING,
    (
        WorkflowState.CONSENSUS_SCORING,
        WorkflowEvent.LOCAL_TRANSLATION_DONE,
    ): WorkflowState.LOCAL_TRANSLATING,
    (
        WorkflowState.INPUT_READY,
        WorkflowEvent.CLOUD_TRANSLATION_DONE,
    ): WorkflowState.CLOUD_TRANSLATING,
    (
        WorkflowState.LOCAL_TRANSLATING,
        WorkflowEvent.CLOUD_TRANSLATION_DONE,
    ): WorkflowState.CLOUD_TRANSLATING,
    (
        WorkflowState.LOCAL_REVIEWING,
        WorkflowEvent.CLOUD_TRANSLATION_DONE,
    ): WorkflowState.CLOUD_TRANSLATING,
    (
        WorkflowState.CONSENSUS_SCORING,
        WorkflowEvent.CLOUD_TRANSLATION_DONE,
    ): WorkflowState.CLOUD_TRANSLATING,
    (
        WorkflowState.CLOUD_TRANSLATING,
        WorkflowEvent.CROSSFIRE_DONE,
    ): WorkflowState.CROSSFIRE_RUNNING,
    (
        WorkflowState.LOCAL_TRANSLATING,
        WorkflowEvent.CONSENSUS_DONE,
    ): WorkflowState.CONSENSUS_SCORING,
    (
        WorkflowState.LOCAL_REVIEWING,
        WorkflowEvent.CONSENSUS_DONE,
    ): WorkflowState.CONSENSUS_SCORING,
    (
        WorkflowState.CROSSFIRE_RUNNING,
        WorkflowEvent.CONSENSUS_DONE,
    ): WorkflowState.CONSENSUS_SCORING,
    (
        WorkflowState.CONSENSUS_SCORING,
        WorkflowEvent.ARBITRATION_DONE,
    ): WorkflowState.WAITING_HUMAN_CONFIRMATION,
    (
        WorkflowState.CONSENSUS_SCORING,
        WorkflowEvent.USER_CONFIRMED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.CONSENSUS_SCORING,
        WorkflowEvent.GLOSSARY_CONFIRMED,
    ): WorkflowState.GLOSSARY_SUGGESTION,
    (
        WorkflowState.WAITING_HUMAN_CONFIRMATION,
        WorkflowEvent.USER_EDITED,
    ): WorkflowState.GLOSSARY_SUGGESTION,
    (
        WorkflowState.WAITING_HUMAN_CONFIRMATION,
        WorkflowEvent.USER_CONFIRMED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.WAITING_HUMAN_CONFIRMATION,
        WorkflowEvent.USER_REJECTED,
    ): WorkflowState.FAILED,
    (
        WorkflowState.GLOSSARY_SUGGESTION,
        WorkflowEvent.GLOSSARY_CONFIRMED,
    ): WorkflowState.COMPLETED,
    (
        WorkflowState.GLOSSARY_SUGGESTION,
        WorkflowEvent.GLOSSARY_SKIPPED,
    ): WorkflowState.COMPLETED,
    (WorkflowState.FAILED, WorkflowEvent.RETRY): WorkflowState.INPUT_READY,
    (WorkflowState.FAILED, WorkflowEvent.RESET): WorkflowState.IDLE,
    (WorkflowState.COMPLETED, WorkflowEvent.RESET): WorkflowState.IDLE,
}

for state in (
    WorkflowState.LOCAL_REVIEWING,
    WorkflowState.CLOUD_TRANSLATING,
    WorkflowState.CROSSFIRE_RUNNING,
    WorkflowState.CONSENSUS_SCORING,
    WorkflowState.WAITING_HUMAN_CONFIRMATION,
    WorkflowState.GLOSSARY_SUGGESTION,
    WorkflowState.COMPLETED,
):
    _TRANSITIONS[(state, WorkflowEvent.RATING_SUBMITTED)] = state

for state in (
    WorkflowState.INPUT_READY,
    WorkflowState.LOCAL_TRANSLATING,
    WorkflowState.LOCAL_REVIEWING,
    WorkflowState.CLOUD_TRANSLATING,
    WorkflowState.CROSSFIRE_RUNNING,
    WorkflowState.CONSENSUS_SCORING,
    WorkflowState.ARBITRATION,
    WorkflowState.WAITING_HUMAN_CONFIRMATION,
    WorkflowState.GLOSSARY_SUGGESTION,
):
    _TRANSITIONS[(state, WorkflowEvent.ERROR_OCCURRED)] = WorkflowState.FAILED
    _TRANSITIONS[(state, WorkflowEvent.RESET)] = WorkflowState.IDLE


def workflow_trace_label(state: WorkflowState) -> str:
    return f"workflow:{state.value}"


@dataclass
class WorkflowStateMachine:
    state: WorkflowState = WorkflowState.IDLE
    history: list[WorkflowState] = field(default_factory=list)

    def apply(self, event: WorkflowEvent) -> WorkflowState:
        next_state = _TRANSITIONS.get((self.state, event))
        if next_state is None:
            raise ValueError(
                f"invalid workflow transition: state={self.state.value} event={event.value}"
            )
        self.state = next_state
        self.history.append(next_state)
        return next_state

    def trace_labels(self) -> list[str]:
        return [workflow_trace_label(state) for state in self.history]
