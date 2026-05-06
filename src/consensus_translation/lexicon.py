from dataclasses import dataclass
import json
from pathlib import Path


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
    def __init__(self, store_path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[2] / "data" / "lexicon.json"
        self._store_path = store_path or default_path
        self._store: dict[str, dict[str, str]] = self._load_store()

    def _load_store(self) -> dict[str, dict[str, str]]:
        if not self._store_path.exists():
            return {}
        with self._store_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}

        parsed: dict[str, dict[str, str]] = {}
        for topic, rows in data.items():
            if isinstance(topic, str) and isinstance(rows, dict):
                parsed[topic] = {
                    key: value
                    for key, value in rows.items()
                    if isinstance(key, str) and isinstance(value, str)
                }
        return parsed

    def _save_store(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._store_path.open("w", encoding="utf-8") as handle:
            json.dump(self._store, handle, ensure_ascii=False, indent=2)

    def apply_revision(self, payload: RevisionPayload) -> RevisionEvent:
        topic = payload.topic or "uncategorized"
        if topic not in self._store:
            self._store[topic] = {}
        self._store[topic][payload.source] = payload.target
        self._save_store()

        special = payload.diff_ratio >= 0.6
        delta = -0.1 if special else 0.05
        return RevisionEvent(special_flag=special, user_prior_delta=delta)

    def find(self, topic: str, source: str) -> str | None:
        if topic not in self._store:
            return None
        return self._store[topic].get(source)
