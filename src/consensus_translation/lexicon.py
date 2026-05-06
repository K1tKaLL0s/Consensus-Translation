from dataclasses import dataclass
import json
import os
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
    _LAYER_KEYS = ("terms", "phrases", "style_rules")

    def __init__(self, store_path: Path | None = None) -> None:
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            default_path = Path(local_app_data) / "ConsensusTranslation" / "lexicon.json"
        else:
            default_path = Path(__file__).resolve().parents[2] / "data" / "lexicon.json"
        self._store_path = store_path or default_path
        self._store: dict[str, dict[str, dict[str, str]]] = self._load_store()

    @classmethod
    def _empty_layers(cls) -> dict[str, dict[str, str]]:
        return {key: {} for key in cls._LAYER_KEYS}

    @classmethod
    def _is_layered_topic(cls, value: object) -> bool:
        if not isinstance(value, dict):
            return False
        return all(k in value for k in cls._LAYER_KEYS)

    def _load_store(self) -> dict[str, dict[str, dict[str, str]]]:
        if not self._store_path.exists():
            return {}
        with self._store_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}

        parsed: dict[str, dict[str, dict[str, str]]] = {}
        for topic, rows in data.items():
            if not isinstance(topic, str) or not isinstance(rows, dict):
                continue

            layers = self._empty_layers()
            if self._is_layered_topic(rows):
                for layer in self._LAYER_KEYS:
                    raw_layer = rows.get(layer)
                    if isinstance(raw_layer, dict):
                        layers[layer] = {
                            key: value
                            for key, value in raw_layer.items()
                            if isinstance(key, str) and isinstance(value, str)
                        }
            else:
                layers["terms"] = {
                    key: value
                    for key, value in rows.items()
                    if isinstance(key, str) and isinstance(value, str)
                }
            parsed[topic] = layers
        return parsed

    def _save_store(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._store_path.open("w", encoding="utf-8") as handle:
            json.dump(self._store, handle, ensure_ascii=False, indent=2)

    def apply_revision(self, payload: RevisionPayload) -> RevisionEvent:
        topic = payload.topic or "uncategorized"
        if topic not in self._store:
            self._store[topic] = self._empty_layers()
        self._store[topic]["terms"][payload.source] = payload.target
        self._save_store()

        special = payload.diff_ratio >= 0.6
        delta = -0.1 if special else 0.05
        return RevisionEvent(special_flag=special, user_prior_delta=delta)

    def find(self, topic: str, source: str) -> str | None:
        if topic not in self._store:
            return None
        return self._store[topic]["terms"].get(source)

    def export_topic(self, topic: str) -> dict[str, dict[str, str]] | None:
        if topic not in self._store:
            return None
        layered = self._store[topic]
        return {
            layer: dict(layered[layer])
            for layer in self._LAYER_KEYS
        }
