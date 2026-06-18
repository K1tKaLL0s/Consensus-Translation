from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_providers import StaticModelProvider
from consensus_translation.agent_store import AgentRunStore
from consensus_translation.agent_workflows import run_agent_translation


def test_sqlite_store_lists_pending_revisions_and_confirms_by_event_id(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    result = run_agent_translation(
        text="Leviathan",
        source_lang="en",
        target_lang="zh",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "Liweitan", confidence=0.8)],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
    )

    pending = store.list_revision_events(confirmed=False)

    assert pending == [
        {
            "id": pending[0]["id"],
            "run_id": result.contract.run_id,
            "topic": "western_myth",
            "layer": "terms",
            "source": "Leviathan",
            "target": "Liweitan",
            "confirmed": False,
        }
    ]
    assert store.confirm_revision_event_by_id(pending[0]["id"]) is True
    assert store.find_lexicon_entry("western_myth", "terms", "Leviathan") == "Liweitan"
    assert store.list_revision_events(confirmed=False) == []
    assert store.list_revision_events(run_id=result.contract.run_id)[0]["confirmed"] is True


def test_sqlite_store_reads_and_confirms_agent_run_status(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "nihao", confidence=0.7)],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
    )

    before = store.get_agent_run(result.contract.run_id)
    confirmed = store.confirm_agent_run(result.contract.run_id)
    after = store.get_agent_run(result.contract.run_id)

    assert before is not None
    assert before["status"] == "awaiting_human_confirmation"
    assert confirmed is True
    assert after is not None
    assert after["status"] == "finalized"
    assert store.confirm_agent_run("missing-run") is False


def test_sqlite_store_imports_json_lexicon_layers_for_agent_lookup(tmp_path):
    json_path = tmp_path / "lexicon.json"
    json_path.write_text(
        """
        {
          "western_myth": {
            "terms": {"Leviathan": "Liweitan"},
            "phrases": {"fallen angel": "duoluo tianshi"},
            "style_rules": {"dialogue": "keep terse"}
          },
          "legacy_topic": {
            "sword": "jian"
          }
        }
        """,
        encoding="utf-8",
    )
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")

    imported = store.import_json_lexicon(json_path)

    assert imported == {
        "terms": 2,
        "phrases": 1,
        "style_rules": 1,
    }
    assert store.export_topic("western_myth") == {
        "terms": {"Leviathan": "Liweitan"},
        "phrases": {"fallen angel": "duoluo tianshi"},
        "style_rules": {"dialogue": "keep terse"},
    }
    assert store.find_lexicon_entry("legacy_topic", "terms", "sword") == "jian"


def test_sqlite_store_records_agent_run_and_pending_revision_events(tmp_path):
    db_path = tmp_path / "agent-runs.sqlite3"
    store = AgentRunStore(db_path)
    result = run_agent_translation(
        text="hello",
        source_lang="en",
        target_lang="zh",
        topic="general",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "你好", confidence=0.7)],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
    )

    with sqlite3.connect(db_path) as conn:
        run_rows = conn.execute(
            "select run_id, mode, status, final_text from agent_runs"
        ).fetchall()
        revision_rows = conn.execute(
            "select run_id, layer, source, target, confirmed from revision_events"
        ).fetchall()

    assert run_rows == [
        (
            result.contract.run_id,
            "learning",
            "awaiting_human_confirmation",
            "你好",
        )
    ]
    assert revision_rows == [
        (result.contract.run_id, "terms", "hello", "你好", 0)
    ]


def test_sqlite_store_creates_lexicon_tables_and_only_writes_after_confirmation(tmp_path):
    db_path = tmp_path / "agent-runs.sqlite3"
    store = AgentRunStore(db_path)
    result = run_agent_translation(
        text="Leviathan",
        source_lang="en",
        target_lang="zh",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "利维坦", confidence=0.8)],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
    )

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }
        terms_before_confirm = conn.execute(
            "select topic, source, target from terms"
        ).fetchall()

    assert {
        "terms",
        "phrases",
        "style_rules",
        "project_profile",
        "agent_runs",
        "revision_events",
    }.issubset(tables)
    assert terms_before_confirm == []

    store.confirm_revision_event(result.contract.run_id, source="Leviathan")

    with sqlite3.connect(db_path) as conn:
        terms_after_confirm = conn.execute(
            "select topic, source, target from terms"
        ).fetchall()
        confirmed_flags = conn.execute(
            "select confirmed from revision_events where run_id = ?",
            (result.contract.run_id,),
        ).fetchall()

    assert terms_after_confirm == [("western_myth", "Leviathan", "利维坦")]
    assert confirmed_flags == [(1,)]
