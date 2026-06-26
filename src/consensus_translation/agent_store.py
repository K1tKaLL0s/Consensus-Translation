from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
from pathlib import Path
import sqlite3

from consensus_translation.agent_contracts import AgentRunResult
from consensus_translation.agent_feedback import (
    RatingSignalSummary,
    TranslationRating,
    TranslationRatingSubmission,
    rating_summary_from_records,
)
from consensus_translation.agent_project import DesktopProjectProfile
from consensus_translation.agent_provider_config import ProviderConfig


class AgentRunStore:
    _LEXICON_LAYERS = ("terms", "phrases", "style_rules")

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    @classmethod
    def _validate_layer(cls, layer: str) -> str:
        if layer not in cls._LEXICON_LAYERS:
            raise ValueError(f"unsupported lexicon layer: {layer}")
        return layer

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _diff_ratio(left: str, right: str) -> float:
        left_text = left.strip()
        right_text = right.strip()
        if not left_text and not right_text:
            return 0.0
        return 1.0 - SequenceMatcher(a=left_text, b=right_text).ratio()

    @staticmethod
    def _ensure_column(
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {
            str(row[1])
            for row in conn.execute(f"pragma table_info({table})").fetchall()
        }
        if column not in columns:
            conn.execute(f"alter table {table} add column {column} {definition}")

    def _init_schema(self) -> None:
        with self._connect() as conn:
            for layer in self._LEXICON_LAYERS:
                conn.execute(
                    f"""
                    create table if not exists {layer} (
                        topic text not null,
                        source text not null,
                        target text not null,
                        primary key(topic, source)
                    )
                    """
                )
                self._ensure_column(conn, layer, "note", "text not null default ''")
                self._ensure_column(conn, layer, "confidence", "real not null default 0.0")
                self._ensure_column(conn, layer, "entry_source", "text not null default 'manual'")
                self._ensure_column(conn, layer, "confirmed_by_user", "integer not null default 1")
                self._ensure_column(conn, layer, "is_special", "integer not null default 0")
                self._ensure_column(conn, layer, "created_at", "text not null default ''")
                self._ensure_column(conn, layer, "updated_at", "text not null default ''")
            conn.execute(
                """
                create table if not exists project_profile (
                    topic text primary key,
                    profile_json text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists provider_configs (
                    provider_id text primary key,
                    kind text not null,
                    base_url text not null,
                    model text not null,
                    credential_id text not null,
                    estimated_cost real not null,
                    enabled integer not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists agent_runs (
                    run_id text primary key,
                    mode text not null,
                    status text not null,
                    final_text text not null,
                    final_score real not null,
                    budget_limit real not null,
                    budget_spent real not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists revision_events (
                    id integer primary key autoincrement,
                    run_id text not null,
                    topic text not null,
                    layer text not null,
                    source text not null,
                    target text not null,
                    confirmed integer not null,
                    foreign key(run_id) references agent_runs(run_id)
                )
                """
            )
            self._ensure_column(conn, "revision_events", "note", "text not null default ''")
            self._ensure_column(conn, "revision_events", "confidence", "real not null default 0.0")
            self._ensure_column(conn, "revision_events", "update_source", "text not null default 'agent_proposal'")
            self._ensure_column(conn, "revision_events", "is_special", "integer not null default 0")
            self._ensure_column(conn, "revision_events", "created_at", "text not null default ''")
            self._ensure_column(conn, "revision_events", "updated_at", "text not null default ''")
            conn.execute(
                """
                create table if not exists translation_ratings (
                    id integer primary key autoincrement,
                    task_id text not null,
                    workflow_run_id text not null,
                    mode text not null,
                    source_language text not null,
                    target_language text not null,
                    topic text not null,
                    rating integer not null,
                    issue_tags_json text not null,
                    dimension_scores_json text not null,
                    comment text not null,
                    mdwc_snapshot_json text not null,
                    provider_snapshot_json text not null,
                    source_text_hash text not null,
                    final_translation_hash text not null,
                    created_at text not null
                )
                """
            )


    @staticmethod
    def _json_load(value: object, default: object) -> object:
        try:
            loaded = json.loads(str(value))
        except (TypeError, json.JSONDecodeError):
            return default
        return loaded

    @classmethod
    def _rating_from_row(cls, row: tuple[object, ...]) -> TranslationRating:
        issue_tags = cls._json_load(row[8], [])
        dimension_scores = cls._json_load(row[9], {})
        mdwc_snapshot = cls._json_load(row[11], {})
        provider_snapshot = cls._json_load(row[12], [])
        return TranslationRating(
            id=int(str(row[0])),
            task_id=str(row[1]),
            workflow_run_id=str(row[2]),
            mode=str(row[3]),
            source_language=str(row[4]),
            target_language=str(row[5]),
            topic=str(row[6]),
            rating=int(str(row[7])),
            issue_tags=tuple(str(item) for item in issue_tags) if isinstance(issue_tags, list) else (),
            dimension_scores={
                str(key): float(value)
                for key, value in dimension_scores.items()
            } if isinstance(dimension_scores, dict) else {},
            comment=str(row[10]),
            mdwc_snapshot=dict(mdwc_snapshot) if isinstance(mdwc_snapshot, dict) else {},
            provider_snapshot=tuple(
                dict(item) for item in provider_snapshot if isinstance(item, dict)
            ) if isinstance(provider_snapshot, list) else (),
            source_text_hash=str(row[13]),
            final_translation_hash=str(row[14]),
            created_at=str(row[15]),
        )

    def record_translation_rating(
        self,
        submission: TranslationRatingSubmission,
    ) -> TranslationRating:
        created_at = self._now()
        rating = TranslationRating.from_submission(
            submission,
            created_at=created_at,
        )
        with self._connect() as conn:
            cursor = conn.execute(
                """
                insert into translation_ratings (
                    task_id, workflow_run_id, mode, source_language, target_language,
                    topic, rating, issue_tags_json, dimension_scores_json, comment,
                    mdwc_snapshot_json, provider_snapshot_json, source_text_hash,
                    final_translation_hash, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rating.task_id,
                    rating.workflow_run_id,
                    rating.mode,
                    rating.source_language,
                    rating.target_language,
                    rating.topic,
                    rating.rating,
                    json.dumps(list(rating.issue_tags), ensure_ascii=False),
                    json.dumps(rating.dimension_scores, ensure_ascii=False, sort_keys=True),
                    rating.comment,
                    json.dumps(rating.mdwc_snapshot, ensure_ascii=False, sort_keys=True),
                    json.dumps(list(rating.provider_snapshot), ensure_ascii=False, sort_keys=True),
                    rating.source_text_hash,
                    rating.final_translation_hash,
                    rating.created_at,
                ),
            )
        return TranslationRating(
            id=int(cursor.lastrowid or 0),
            task_id=rating.task_id,
            workflow_run_id=rating.workflow_run_id,
            mode=rating.mode,
            source_language=rating.source_language,
            target_language=rating.target_language,
            topic=rating.topic,
            rating=rating.rating,
            issue_tags=rating.issue_tags,
            dimension_scores=rating.dimension_scores,
            comment=rating.comment,
            mdwc_snapshot=rating.mdwc_snapshot,
            provider_snapshot=rating.provider_snapshot,
            source_text_hash=rating.source_text_hash,
            final_translation_hash=rating.final_translation_hash,
            created_at=rating.created_at,
        )

    def skip_translation_rating(self, workflow_run_id: str) -> None:
        return None

    def _list_rating_objects(self) -> list[TranslationRating]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id, task_id, workflow_run_id, mode, source_language,
                       target_language, topic, rating, issue_tags_json,
                       dimension_scores_json, comment, mdwc_snapshot_json,
                       provider_snapshot_json, source_text_hash,
                       final_translation_hash, created_at
                from translation_ratings
                order by id
                """
            ).fetchall()
        return [self._rating_from_row(row) for row in rows]

    def list_translation_ratings(self) -> list[dict[str, object]]:
        return [rating.to_spec_dict() for rating in self._list_rating_objects()]

    def rating_signal_summary(
        self,
        *,
        topic: str,
        source_language: str,
        target_language: str,
        mode: str,
        provider_ids: tuple[str, ...] = (),
    ) -> RatingSignalSummary:
        return rating_summary_from_records(
            self._list_rating_objects(),
            topic=topic,
            source_language=source_language,
            target_language=target_language,
            mode=mode,
            provider_ids=provider_ids,
        )

    def upsert_provider_config(self, config: ProviderConfig) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into provider_configs (
                    provider_id, kind, base_url, model, credential_id, estimated_cost, enabled
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    config.provider_id,
                    config.kind,
                    config.base_url,
                    config.model,
                    config.credential_id,
                    config.estimated_cost,
                    1 if config.enabled else 0,
                ),
            )

    def list_provider_configs(
        self,
        enabled: bool | None = None,
    ) -> list[ProviderConfig]:
        clauses: list[str] = []
        params: list[object] = []
        if enabled is not None:
            clauses.append("enabled = ?")
            params.append(1 if enabled else 0)
        where_clause = ""
        if clauses:
            where_clause = "where " + " and ".join(clauses)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select provider_id, kind, base_url, model, credential_id, estimated_cost, enabled
                from provider_configs
                {where_clause}
                order by provider_id
                """,
                params,
            ).fetchall()
        return [
            ProviderConfig(
                provider_id=str(row[0]),
                kind=str(row[1]),
                base_url=str(row[2]),
                model=str(row[3]),
                credential_id=str(row[4]),
                estimated_cost=float(row[5]),
                enabled=bool(row[6]),
            )
            for row in rows
        ]

    def save_project_profile(self, profile: DesktopProjectProfile) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into project_profile (topic, profile_json)
                values (?, ?)
                """,
                (
                    profile.project_id,
                    json.dumps(
                        profile.to_json_dict(),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )

    def get_project_profile(self, project_id: str = "default") -> DesktopProjectProfile | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select profile_json
                from project_profile
                where topic = ?
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        raw = json.loads(str(row[0]))
        if not isinstance(raw, dict):
            return None
        return DesktopProjectProfile.from_json_dict(raw)

    def upsert_lexicon_entry(
        self,
        topic: str | None,
        layer: str,
        source: str,
        target: str,
        *,
        note: str = "",
        confidence: float = 0.0,
        entry_source: str = "manual",
        confirmed_by_user: bool = True,
        is_special: bool = False,
    ) -> None:
        table = self._validate_layer(layer)
        normalized_topic = topic or "uncategorized"
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                f"""
                insert into {table} (
                    topic, source, target, note, confidence, entry_source,
                    confirmed_by_user, is_special, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(topic, source) do update set
                    target = excluded.target,
                    note = excluded.note,
                    confidence = excluded.confidence,
                    entry_source = excluded.entry_source,
                    confirmed_by_user = excluded.confirmed_by_user,
                    is_special = excluded.is_special,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_topic,
                    source,
                    target,
                    note,
                    float(confidence),
                    entry_source,
                    1 if confirmed_by_user else 0,
                    1 if is_special else 0,
                    now,
                    now,
                ),
            )

    @staticmethod
    def _bool_metadata_value(value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "y"}:
                return True
            if lowered in {"0", "false", "no", "n"}:
                return False
        return default

    def _import_lexicon_value(
        self,
        topic: str,
        layer: str,
        source: str,
        value: object,
    ) -> bool:
        if isinstance(value, str):
            self.upsert_lexicon_entry(topic, layer, source, value)
            return True
        if not isinstance(value, dict):
            return False
        target = value.get("target", value.get("translation", ""))
        if not isinstance(target, str) or not target:
            return False
        raw_confidence = value.get("confidence", 0.0)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        entry_source = value.get("entry_source", value.get("source", "import"))
        self.upsert_lexicon_entry(
            topic,
            layer,
            source,
            target,
            note=str(value.get("note", "")),
            confidence=confidence,
            entry_source=str(entry_source or "import"),
            confirmed_by_user=self._bool_metadata_value(
                value.get("confirmed_by_user"),
                True,
            ),
            is_special=self._bool_metadata_value(value.get("is_special"), False),
        )
        return True

    def import_json_lexicon(self, json_path: str | Path) -> dict[str, int]:
        path = Path(json_path)
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        counts = {layer: 0 for layer in self._LEXICON_LAYERS}
        if not isinstance(data, dict):
            return counts

        for topic, rows in data.items():
            if not isinstance(topic, str) or not isinstance(rows, dict):
                continue

            has_layer_dict = any(
                isinstance(rows.get(layer), dict) for layer in self._LEXICON_LAYERS
            )
            if has_layer_dict:
                for layer in self._LEXICON_LAYERS:
                    raw_layer = rows.get(layer)
                    if not isinstance(raw_layer, dict):
                        continue
                    for source, value in raw_layer.items():
                        if isinstance(source, str) and self._import_lexicon_value(
                            topic,
                            layer,
                            source,
                            value,
                        ):
                            counts[layer] += 1
                continue

            for source, value in rows.items():
                if isinstance(source, str) and self._import_lexicon_value(
                    topic,
                    "terms",
                    source,
                    value,
                ):
                    counts["terms"] += 1

        return counts
    def find_lexicon_entry(
        self,
        topic: str | None,
        layer: str,
        source: str,
    ) -> str | None:
        table = self._validate_layer(layer)
        normalized_topic = topic or "uncategorized"
        with self._connect() as conn:
            row = conn.execute(
                f"""
                select target
                from {table}
                where topic = ? and source = ?
                """,
                (normalized_topic, source),
            ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def export_topic(self, topic: str | None) -> dict[str, dict[str, str]]:
        normalized_topic = topic or "uncategorized"
        exported: dict[str, dict[str, str]] = {}
        with self._connect() as conn:
            for layer in self._LEXICON_LAYERS:
                rows = conn.execute(
                    f"""
                    select source, target
                    from {layer}
                    where topic = ?
                    order by source
                    """,
                    (normalized_topic,),
                ).fetchall()
                exported[layer] = {str(source): str(target) for source, target in rows}
        return exported

    def export_topic_entries(self, topic: str | None) -> dict[str, list[dict[str, object]]]:
        normalized_topic = topic or "uncategorized"
        exported: dict[str, list[dict[str, object]]] = {}
        with self._connect() as conn:
            for layer in self._LEXICON_LAYERS:
                rows = conn.execute(
                    f"""
                    select source, target, note, confidence, entry_source,
                           confirmed_by_user, is_special, created_at, updated_at
                    from {layer}
                    where topic = ?
                    order by source
                    """,
                    (normalized_topic,),
                ).fetchall()
                exported[layer] = [
                    {
                        "source": row[0],
                        "target": row[1],
                        "note": row[2],
                        "confidence": float(row[3]),
                        "entry_source": row[4],
                        "confirmed_by_user": bool(row[5]),
                        "is_special": bool(row[6]),
                        "created_at": row[7],
                        "updated_at": row[8],
                    }
                    for row in rows
                ]
        return exported

    def export_all_lexicon_entries(self) -> dict[str, dict[str, dict[str, dict[str, object]]]]:
        exported: dict[str, dict[str, dict[str, dict[str, object]]]] = {}
        with self._connect() as conn:
            for layer in self._LEXICON_LAYERS:
                rows = conn.execute(
                    f"""
                    select topic, source, target, note, confidence, entry_source,
                           confirmed_by_user, is_special, created_at, updated_at
                    from {layer}
                    order by topic, source
                    """
                ).fetchall()
                for row in rows:
                    topic = str(row[0])
                    source = str(row[1])
                    topic_rows = exported.setdefault(
                        topic,
                        {name: {} for name in self._LEXICON_LAYERS},
                    )
                    topic_rows[layer][source] = {
                        "target": row[2],
                        "note": row[3],
                        "confidence": float(row[4]),
                        "entry_source": row[5],
                        "confirmed_by_user": bool(row[6]),
                        "is_special": bool(row[7]),
                        "created_at": row[8],
                        "updated_at": row[9],
                    }
        return exported
    def find_matching_lexicon_entries(
        self,
        topic: str | None,
        text: str,
    ) -> dict[str, dict[str, str]]:
        topic_entries = self.export_topic(topic)
        return {
            layer: {
                source: target
                for source, target in entries.items()
                if source and source in text
            }
            for layer, entries in topic_entries.items()
        }

    def count_special_entries(self, topic: str | None, text: str) -> int:
        normalized_topic = topic or "uncategorized"
        count = 0
        with self._connect() as conn:
            for layer in self._LEXICON_LAYERS:
                rows = conn.execute(
                    f"""
                    select source
                    from {layer}
                    where topic = ? and is_special = 1
                    """,
                    (normalized_topic,),
                ).fetchall()
                count += sum(1 for row in rows if str(row[0]) and str(row[0]) in text)
        return count
    def count_user_corrections(self, topic: str | None, text: str) -> int:
        normalized_topic = topic or "uncategorized"
        with self._connect() as conn:
            rows = conn.execute(
                """
                select source
                from revision_events
                where topic = ? and update_source = 'user_correction' and confirmed = 1
                """,
                (normalized_topic,),
            ).fetchall()
        return sum(1 for row in rows if str(row[0]) and str(row[0]) in text)

    def _insert_revision_event(
        self,
        conn: sqlite3.Connection,
        *,
        run_id: str,
        topic: str | None,
        layer: str,
        source: str,
        target: str,
        confirmed: bool,
        note: str,
        confidence: float,
        update_source: str,
        is_special: bool,
    ) -> int:
        table = self._validate_layer(layer)
        now = self._now()
        cursor = conn.execute(
            """
            insert into revision_events (
                run_id, topic, layer, source, target, confirmed, note,
                confidence, update_source, is_special, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                topic or "uncategorized",
                table,
                source,
                target,
                1 if confirmed else 0,
                note,
                float(confidence),
                update_source,
                1 if is_special else 0,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid or 0)

    def record_user_correction(
        self,
        *,
        run_id: str,
        topic: str | None,
        source: str,
        provisional_text: str,
        revised_text: str,
        layer: str = "terms",
    ) -> int:
        ratio = self._diff_ratio(provisional_text, revised_text)
        is_special = ratio >= 0.6
        with self._connect() as conn:
            return self._insert_revision_event(
                conn,
                run_id=run_id,
                topic=topic,
                layer=layer,
                source=source,
                target=revised_text,
                confirmed=False,
                note=f"diff_ratio={ratio:.6f}",
                confidence=1.0,
                update_source="user_correction",
                is_special=is_special,
            )

    def record_result(self, result: AgentRunResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert or replace into agent_runs (
                    run_id, mode, status, final_text, final_score, budget_limit, budget_spent
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.contract.run_id,
                    result.contract.mode.value,
                    result.contract.status.value,
                    result.decision.final_text,
                    result.decision.final_score,
                    result.contract.budget["limit"],
                    result.contract.budget["spent"],
                ),
            )
            for proposal in result.lexicon_proposals:
                self._insert_revision_event(
                    conn,
                    run_id=result.contract.run_id,
                    topic=proposal.topic,
                    layer=proposal.layer,
                    source=proposal.source,
                    target=proposal.target,
                    confirmed=not proposal.requires_user_confirm,
                    note=proposal.rationale,
                    confidence=proposal.confidence,
                    update_source=proposal.update_source,
                    is_special=proposal.is_special,
                )

    def _confirm_revision_row(self, conn: sqlite3.Connection, row: tuple[object, ...]) -> None:
        (
            event_id,
            topic,
            layer,
            source,
            target,
            note,
            confidence,
            update_source,
            is_special,
        ) = row
        self.upsert_lexicon_entry(
            str(topic),
            str(layer),
            str(source),
            str(target),
            note=str(note),
            confidence=float(str(confidence)),
            entry_source=str(update_source),
            confirmed_by_user=True,
            is_special=bool(is_special),
        )
        conn.execute(
            "update revision_events set confirmed = 1, updated_at = ? where id = ?",
            (self._now(), event_id),
        )

    def confirm_revision_event(self, run_id: str, source: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id, topic, layer, source, target, note, confidence,
                       update_source, is_special
                from revision_events
                where run_id = ? and source = ? and confirmed = 0
                order by id
                limit 1
                """,
                (run_id, source),
            ).fetchone()
            if row is None:
                return
            self._confirm_revision_row(conn, row)

    def confirm_revision_event_by_id(self, event_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id, topic, layer, source, target, note, confidence,
                       update_source, is_special
                from revision_events
                where id = ? and confirmed = 0
                """,
                (event_id,),
            ).fetchone()
            if row is None:
                return False
            self._confirm_revision_row(conn, row)
        return True


    def skip_revision_event_by_id(self, event_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "delete from revision_events where id = ? and confirmed = 0",
                (event_id,),
            )
        return cursor.rowcount > 0

    def mark_revision_event_special_by_id(self, event_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                update revision_events
                set is_special = 1, updated_at = ?
                where id = ? and confirmed = 0
                """
                ,
                (self._now(), event_id),
            )
        return cursor.rowcount > 0

    def list_revision_events(
        self,
        confirmed: bool | None = None,
        run_id: str | None = None,
    ) -> list[dict[str, object]]:
        clauses: list[str] = []
        params: list[object] = []
        if confirmed is not None:
            clauses.append("confirmed = ?")
            params.append(1 if confirmed else 0)
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        where_clause = ""
        if clauses:
            where_clause = "where " + " and ".join(clauses)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select id, run_id, topic, layer, source, target, confirmed,
                       note, confidence, update_source, is_special, created_at, updated_at
                from revision_events
                {where_clause}
                order by id
                """,
                params,
            ).fetchall()
        return [
            {
                "id": row[0],
                "run_id": row[1],
                "topic": row[2],
                "layer": row[3],
                "source": row[4],
                "target": row[5],
                "confirmed": bool(row[6]),
                "note": row[7],
                "confidence": float(row[8]),
                "update_source": row[9],
                "is_special": bool(row[10]),
                "created_at": row[11],
                "updated_at": row[12],
            }
            for row in rows
        ]

    @staticmethod
    def _run_row_to_dict(row: tuple[object, ...]) -> dict[str, object]:
        return {
            "run_id": row[0],
            "mode": row[1],
            "status": row[2],
            "final_text": row[3],
            "final_score": row[4],
            "budget_limit": row[5],
            "budget_spent": row[6],
        }

    def get_agent_run(self, run_id: str) -> dict[str, object] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select run_id, mode, status, final_text, final_score, budget_limit, budget_spent
                from agent_runs
                where run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return self._run_row_to_dict(row)

    def confirm_agent_run(self, run_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                update agent_runs
                set status = 'finalized'
                where run_id = ?
                  and status in ('awaiting_human_confirmation', 'needs_review')
                """,
                (run_id,),
            )
        return cursor.rowcount > 0

    def reject_agent_run(self, run_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                update agent_runs
                set status = 'rejected'
                where run_id = ? and status != 'finalized'
                """,
                (run_id,),
            )
        return cursor.rowcount > 0

    def list_agent_runs(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select run_id, mode, status, final_text, final_score, budget_limit, budget_spent
                from agent_runs
                order by rowid
                """
            ).fetchall()
        return [self._run_row_to_dict(row) for row in rows]
