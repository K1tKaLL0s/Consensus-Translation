from __future__ import annotations

import sqlite3
import json
from pathlib import Path

from consensus_translation.agent_contracts import AgentRunResult
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

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists terms (
                    topic text not null,
                    source text not null,
                    target text not null,
                    primary key(topic, source)
                )
                """
            )
            conn.execute(
                """
                create table if not exists phrases (
                    topic text not null,
                    source text not null,
                    target text not null,
                    primary key(topic, source)
                )
                """
            )
            conn.execute(
                """
                create table if not exists style_rules (
                    topic text not null,
                    source text not null,
                    target text not null,
                    primary key(topic, source)
                )
                """
            )
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
    ) -> None:
        table = self._validate_layer(layer)
        normalized_topic = topic or "uncategorized"
        with self._connect() as conn:
            conn.execute(
                f"""
                insert or replace into {table} (topic, source, target)
                values (?, ?, ?)
                """,
                (normalized_topic, source, target),
            )

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
                    for source, target in raw_layer.items():
                        if isinstance(source, str) and isinstance(target, str):
                            self.upsert_lexicon_entry(topic, layer, source, target)
                            counts[layer] += 1
                continue

            for source, target in rows.items():
                if isinstance(source, str) and isinstance(target, str):
                    self.upsert_lexicon_entry(topic, "terms", source, target)
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
                conn.execute(
                    """
                    insert into revision_events (
                        run_id, topic, layer, source, target, confirmed
                    ) values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.contract.run_id,
                        proposal.topic,
                        proposal.layer,
                        proposal.source,
                        proposal.target,
                        0 if proposal.requires_user_confirm else 1,
                    ),
                )

    def confirm_revision_event(self, run_id: str, source: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id, topic, layer, source, target
                from revision_events
                where run_id = ? and source = ? and confirmed = 0
                order by id
                limit 1
                """,
                (run_id, source),
            ).fetchone()
            if row is None:
                return

            event_id, topic, layer, event_source, target = row
            table = self._validate_layer(layer)

            conn.execute(
                f"""
                insert or replace into {table} (topic, source, target)
                values (?, ?, ?)
                """,
                (topic, event_source, target),
            )
            conn.execute(
                "update revision_events set confirmed = 1 where id = ?",
                (event_id,),
            )

    def confirm_revision_event_by_id(self, event_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id, topic, layer, source, target
                from revision_events
                where id = ? and confirmed = 0
                """,
                (event_id,),
            ).fetchone()
            if row is None:
                return False

            _, topic, layer, source, target = row
            table = self._validate_layer(layer)
            conn.execute(
                f"""
                insert or replace into {table} (topic, source, target)
                values (?, ?, ?)
                """,
                (topic, source, target),
            )
            conn.execute(
                "update revision_events set confirmed = 1 where id = ?",
                (event_id,),
            )
        return True

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
                select id, run_id, topic, layer, source, target, confirmed
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
