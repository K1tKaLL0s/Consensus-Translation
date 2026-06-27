from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from consensus_translation.agent_store import AgentRunStore
from consensus_translation.desktop_agent_app import default_desktop_store_path


def default_legacy_lexicon_path() -> Path:
    from consensus_translation.lexicon import LexiconRepo

    return LexiconRepo()._store_path


@dataclass(frozen=True)
class LexiconMigrationReport:
    source_path: Path
    db_path: Path
    imported_counts: dict[str, int]

    def to_json_dict(self) -> dict[str, object]:
        return {
            "source_path": str(self.source_path),
            "db_path": str(self.db_path),
            "imported_counts": dict(self.imported_counts),
        }


def migrate_legacy_json_lexicon(
    source_path: str | Path | None = None,
    db_path: str | Path | None = None,
) -> LexiconMigrationReport:
    source = Path(source_path) if source_path is not None else default_legacy_lexicon_path()
    target_db = Path(db_path) if db_path is not None else default_desktop_store_path()
    store = AgentRunStore(target_db)
    imported_counts = store.import_json_lexicon(source)
    return LexiconMigrationReport(
        source_path=source,
        db_path=target_db,
        imported_counts=imported_counts,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate legacy JSON lexicon entries into the desktop agent SQLite store.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Path to legacy lexicon.json. Defaults to the existing LexiconRepo path.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to agent SQLite DB. Defaults to the desktop store path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = migrate_legacy_json_lexicon(args.source, args.db)
    print(json.dumps(report.to_json_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
