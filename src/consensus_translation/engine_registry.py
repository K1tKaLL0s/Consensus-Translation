from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class EngineDescriptor:
    engine_id: str
    provider_kind: str
    model_ids: tuple[str, ...]
    license_id: str
    commercial_use: bool
    bundled: bool
    requires_license_acceptance: bool


class EngineRegistry:
    def __init__(self, entries: Sequence[EngineDescriptor]) -> None:
        self._entries = {entry.engine_id: entry for entry in entries}

    @classmethod
    def default(cls) -> "EngineRegistry":
        commercial_models = (
            "Helsinki-NLP/opus-mt-zh-en",
            "Helsinki-NLP/opus-mt-en-zh",
            "Helsinki-NLP/opus-mt-ja-en",
            "Helsinki-NLP/opus-mt-en-jap",
            "Helsinki-NLP/opus-mt-tc-big-zh-ja",
        )
        pivot_models = (
            "Helsinki-NLP/opus-mt-zh-en",
            "Helsinki-NLP/opus-mt-en-zh",
            "Helsinki-NLP/opus-mt-ja-en",
            "Helsinki-NLP/opus-mt-en-jap",
        )
        return cls(
            [
                EngineDescriptor(
                    engine_id="marian-opus-direct",
                    provider_kind="local",
                    model_ids=commercial_models,
                    license_id="Apache-2.0/CC-BY-4.0",
                    commercial_use=True,
                    bundled=False,
                    requires_license_acceptance=False,
                ),
                EngineDescriptor(
                    engine_id="marian-opus-pivot",
                    provider_kind="local",
                    model_ids=pivot_models,
                    license_id="Apache-2.0/CC-BY-4.0",
                    commercial_use=True,
                    bundled=False,
                    requires_license_acceptance=False,
                ),
                EngineDescriptor(
                    engine_id="nllb-200-distilled-600m",
                    provider_kind="local",
                    model_ids=("facebook/nllb-200-distilled-600M",),
                    license_id="CC-BY-NC-4.0",
                    commercial_use=False,
                    bundled=False,
                    requires_license_acceptance=True,
                ),
            ]
        )

    def enabled_for(self, profile: str) -> list[EngineDescriptor]:
        normalized = profile.strip().lower()
        if normalized == "commercial-safe":
            return [
                entry
                for entry in self._entries.values()
                if entry.commercial_use
            ]
        if normalized == "research":
            return list(self._entries.values())
        raise ValueError(f"unknown release profile: {profile}")

    def get(self, engine_id: str) -> EngineDescriptor:
        return self._entries[engine_id]
