from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from consensus_translation.agent_contracts import AgentRunResult
from consensus_translation.agent_feedback import TranslationRatingSubmission
from consensus_translation.agent_finalize import (
    finalizable_agent_run_statuses,
    finalized_agent_run_status,
)
from consensus_translation.product_contracts import ErrorCode, FinalizeEventDTO, map_task_status


def commit_agent_result(store: object | None, result: AgentRunResult) -> FinalizeEventDTO:
    if store is None:
        return FinalizeEventDTO(
            event_type="store_commit",
            task_status=map_task_status(result.contract.status.value),
            run_id=result.contract.run_id,
        )
    recorder = getattr(store, "record_result", None)
    if callable(recorder):
        recorder(result)
    return FinalizeEventDTO(
        event_type="store_commit",
        task_status=map_task_status(result.contract.status.value),
        run_id=result.contract.run_id,
    )


class FinalizeService:
    def __init__(
        self,
        *,
        agent_store: object | None = None,
        lexicon_store: object | None = None,
        history_store: object | None = None,
    ) -> None:
        self.agent_store = agent_store
        self.lexicon_store = lexicon_store or agent_store
        self.history_store = history_store

    def commit_agent_result(self, result: AgentRunResult) -> FinalizeEventDTO:
        return commit_agent_result(self.agent_store, result)

    def confirm_run(self, run_id: str) -> bool:
        confirmer = getattr(self.agent_store, "confirm_agent_run", None)
        return bool(callable(confirmer) and confirmer(run_id))

    def confirm_lexicon_update(self, event_id: int) -> bool:
        confirmer = getattr(self.lexicon_store, "confirm_revision_event_by_id", None)
        return bool(callable(confirmer) and confirmer(event_id))

    def commit_translation_history(self, **payload: object) -> object:
        writer = getattr(self.history_store, "add", None)
        if not callable(writer):
            raise ValueError("translation history requires a history store")
        return writer(**payload)

    def submit_rating(
        self,
        *,
        run: object,
        mode: str,
        source_language: str,
        target_language: str,
        topic: str,
        source_text: str,
        final_translation: str,
        rating: int,
        issue_tags: tuple[str, ...] = (),
        dimension_scores: dict[str, float] | None = None,
        comment: str = "",
    ) -> object:
        recorder = getattr(self.agent_store, "record_translation_rating", None)
        if not callable(recorder):
            raise ValueError("translation rating requires an AgentRunStore")
        contract = getattr(run, "contract")
        decision = getattr(run, "decision")
        candidates = getattr(run, "candidates")
        provider_snapshot = [
            {
                "providerId": candidate.provider_id,
                "confidence": candidate.confidence,
                "providerKind": candidate.provider_kind,
                "providerRole": candidate.provider_role,
                "isMock": candidate.is_mock,
            }
            for candidate in candidates
        ]
        mdwc_snapshot = {
            "finalScore": decision.final_score,
            "confidenceLevel": decision.confidence_level,
            "conflicts": list(decision.conflict_points),
            "arbitrationReason": decision.arbitration_reason,
            "scoringDimensions": dict(decision.scoring_dimensions),
        }
        stored = recorder(
            TranslationRatingSubmission(
                task_id=contract.run_id,
                workflow_run_id=contract.run_id,
                mode=mode,
                source_language=source_language,
                target_language=target_language,
                topic=topic or "uncategorized",
                rating=rating,
                issue_tags=tuple(issue_tags),
                dimension_scores=dict(dimension_scores or {}),
                comment=comment,
                mdwc_snapshot=mdwc_snapshot,
                provider_snapshot=provider_snapshot,
                source_text=source_text,
                final_translation=final_translation,
            )
        )
        attacher = getattr(self.history_store, "attach_rating", None)
        if callable(attacher):
            attacher(
                run_id=contract.run_id,
                rating=rating,
                issue_tags=tuple(issue_tags),
                comment=comment,
            )
        return stored

    def skip_rating(self, run_id: str) -> None:
        skipper = getattr(self.agent_store, "skip_translation_rating", None)
        if callable(skipper):
            skipper(run_id)
        return None

    def skip_translation_rating(self, run_id: str) -> None:
        return self.skip_rating(run_id)

    def export_lexicon_to_file(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        exporter = getattr(self.lexicon_store, "export_all_lexicon_entries", None)
        payload: Any = exporter() if callable(exporter) else {}
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return destination

    def import_lexicon_from_file(self, path: str | Path) -> dict[str, int]:
        importer = getattr(self.lexicon_store, "import_json_lexicon", None)
        empty = {"terms": 0, "phrases": 0, "style_rules": 0}
        if not callable(importer):
            return empty
        imported = importer(path)
        if not isinstance(imported, dict):
            return empty
        return {layer: int(imported.get(layer, 0)) for layer in empty}

    def finalize_status_contract(self) -> dict[str, object]:
        return {
            "finalized": finalized_agent_run_status(),
            "finalizable": finalizable_agent_run_statuses(),
            "error_code": ErrorCode.NONE.value,
        }
