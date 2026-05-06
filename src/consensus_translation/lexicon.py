from dataclasses import dataclass


@dataclass
class RevisionPayload:
    topic: str | None
    source: str
    target: str
    diff_ratio: float


@dataclass
class RevisionEvent:
    special_flag: bool
    user_prior_delta: float


class LexiconRepo:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}

    def apply_revision(self, payload: RevisionPayload) -> RevisionEvent:
        topic = payload.topic or "uncategorized"
        if topic not in self._store:
            self._store[topic] = {}
        self._store[topic][payload.source] = payload.target

        special = payload.diff_ratio >= 0.6
        delta = -0.1 if special else 0.05
        return RevisionEvent(special_flag=special, user_prior_delta=delta)

    def find(self, topic: str, source: str) -> str | None:
        if topic not in self._store:
            return None
        return self._store[topic].get(source)
