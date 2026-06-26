from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_lexicon_migration import (
    main as migration_main,
    migrate_legacy_json_lexicon,
)
from consensus_translation.agent_store import AgentRunStore


def test_migrate_legacy_json_lexicon_imports_layers_into_sqlite(tmp_path):
    source = tmp_path / "lexicon.json"
    source.write_text(
        json.dumps(
            {
                "western_myth": {
                    "terms": {"Leviathan": "Liweitan"},
                    "phrases": {"fallen angel": "duoluo tianshi"},
                    "style_rules": {"dialogue": "keep terse"},
                },
                "legacy_topic": {"sword": "jian"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "agent.sqlite3"

    report = migrate_legacy_json_lexicon(source, db_path)

    assert report.source_path == source
    assert report.db_path == db_path
    assert report.imported_counts == {
        "terms": 2,
        "phrases": 1,
        "style_rules": 1,
    }
    store = AgentRunStore(db_path)
    assert store.export_topic("western_myth") == {
        "terms": {"Leviathan": "Liweitan"},
        "phrases": {"fallen angel": "duoluo tianshi"},
        "style_rules": {"dialogue": "keep terse"},
    }
    assert store.find_lexicon_entry("legacy_topic", "terms", "sword") == "jian"


def test_lexicon_migration_cli_prints_json_summary(tmp_path, capsys):
    source = tmp_path / "lexicon.json"
    source.write_text(
        json.dumps({"general": {"hello": "nihao"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    db_path = tmp_path / "agent.sqlite3"

    exit_code = migration_main(
        ["--source", str(source), "--db", str(db_path)]
    )

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured == {
        "source_path": str(source),
        "db_path": str(db_path),
        "imported_counts": {
            "terms": 1,
            "phrases": 0,
            "style_rules": 0,
        },
    }


def test_windows_migration_script_exists_and_invokes_module():
    script = ROOT / "migrate_legacy_lexicon.ps1"

    content = script.read_text(encoding="utf-8")

    assert "consensus_translation.agent_lexicon_migration" in content
