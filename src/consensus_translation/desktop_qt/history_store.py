from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class TranslationHistoryRecord:
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    created_at: str
    topic: str = ""
    mode: str = ""
    run_id: str = ""
    workflow_status: str = ""
    workflow_steps: tuple[str, ...] = ()
    consensus_score: float | None = None
    confidence_level: str = ""
    conflicts: tuple[str, ...] = ()
    arbitration_reason: str = ""
    requires_human_review: bool = False
    rating: int | None = None
    rating_issue_tags: tuple[str, ...] = ()
    rating_comment: str = ""


class TranslationHistoryStore:
    def __init__(self, path: str | Path, limit: int = 20) -> None:
        self.path = Path(path)
        self.limit = limit

    def add(
        self,
        *,
        source_text: str,
        translated_text: str,
        source_language: str,
        target_language: str,
        topic: str = "",
        mode: str = "",
        run_id: str = "",
        workflow_status: str = "",
        workflow_steps: tuple[str, ...] = (),
        consensus_score: float | None = None,
        confidence_level: str = "",
        conflicts: tuple[str, ...] = (),
        arbitration_reason: str = "",
        requires_human_review: bool = False,
        rating: int | None = None,
        rating_issue_tags: tuple[str, ...] = (),
        rating_comment: str = "",
    ) -> TranslationHistoryRecord:
        record = TranslationHistoryRecord(
            source_text=source_text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=target_language,
            created_at=datetime.now(timezone.utc).isoformat(),
            topic=topic,
            mode=mode,
            run_id=run_id,
            workflow_status=workflow_status,
            workflow_steps=tuple(workflow_steps),
            consensus_score=consensus_score,
            confidence_level=confidence_level,
            conflicts=tuple(conflicts),
            arbitration_reason=arbitration_reason,
            requires_human_review=requires_human_review,
            rating=rating,
            rating_issue_tags=tuple(rating_issue_tags),
            rating_comment=rating_comment,
        )
        records = [record, *self.list_recent()]
        self._write(records[: self.limit])
        return record

    def list_recent(self) -> list[TranslationHistoryRecord]:
        if not self.path.is_file():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        records: list[TranslationHistoryRecord] = []
        for item in payload[: self.limit]:
            if not isinstance(item, dict):
                continue
            try:
                records.append(
                    TranslationHistoryRecord(
                        source_text=str(item["source_text"]),
                        translated_text=str(item["translated_text"]),
                        source_language=str(item["source_language"]),
                        target_language=str(item["target_language"]),
                        created_at=str(item["created_at"]),
                        topic=str(item.get("topic", "")),
                        mode=str(item.get("mode", "")),
                        run_id=str(item.get("run_id", "")),
                        workflow_status=str(item.get("workflow_status", "")),
                        workflow_steps=_string_tuple(item.get("workflow_steps", ())),
                        consensus_score=_optional_float(item.get("consensus_score")),
                        confidence_level=str(item.get("confidence_level", "")),
                        conflicts=_string_tuple(item.get("conflicts", ())),
                        arbitration_reason=str(item.get("arbitration_reason", "")),
                        requires_human_review=_bool_value(
                            item.get("requires_human_review"),
                        ),
                        rating=_optional_int(item.get("rating")),
                        rating_issue_tags=_string_tuple(
                            item.get("rating_issue_tags", ()),
                        ),
                        rating_comment=str(item.get("rating_comment", "")),
                    )
                )
            except (KeyError, TypeError):
                continue
        return records

    def attach_rating(
        self,
        *,
        run_id: str,
        rating: int,
        issue_tags: tuple[str, ...] = (),
        comment: str = "",
    ) -> bool:
        records = self.list_recent()
        updated: list[TranslationHistoryRecord] = []
        changed = False
        for record in records:
            if record.run_id == run_id and not changed:
                updated.append(
                    TranslationHistoryRecord(
                        source_text=record.source_text,
                        translated_text=record.translated_text,
                        source_language=record.source_language,
                        target_language=record.target_language,
                        created_at=record.created_at,
                        topic=record.topic,
                        mode=record.mode,
                        run_id=record.run_id,
                        workflow_status=record.workflow_status,
                        workflow_steps=record.workflow_steps,
                        consensus_score=record.consensus_score,
                        confidence_level=record.confidence_level,
                        conflicts=record.conflicts,
                        arbitration_reason=record.arbitration_reason,
                        requires_human_review=record.requires_human_review,
                        rating=rating,
                        rating_issue_tags=tuple(issue_tags),
                        rating_comment=comment,
                    )
                )
                changed = True
            else:
                updated.append(record)
        if changed:
            self._write(updated)
        return changed

    def clear(self) -> None:
        self._write([])

    def _write(self, records: list[TranslationHistoryRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                [asdict(record) for record in records],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple, set)):
        return ()
    return tuple(str(item) for item in value if str(item))


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)

def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
