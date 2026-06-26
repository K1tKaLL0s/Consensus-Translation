import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.agent_contracts import AgentMode
from consensus_translation.agent_feedback import TranslationRatingSubmission
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

    assert pending[0] == {
        "id": pending[0]["id"],
        "run_id": result.contract.run_id,
        "topic": "western_myth",
        "layer": "terms",
        "source": "Leviathan",
        "target": "Liweitan",
        "confirmed": False,
        "note": "agent-final-candidate",
        "confidence": result.decision.final_score,
        "update_source": "agent_proposal",
        "is_special": False,
        "created_at": pending[0]["created_at"],
        "updated_at": pending[0]["updated_at"],
    }
    assert store.confirm_revision_event_by_id(pending[0]["id"]) is True
    assert store.find_lexicon_entry("western_myth", "terms", "Leviathan") == "Liweitan"
    assert store.list_revision_events(confirmed=False) == []
    assert store.list_revision_events(run_id=result.contract.run_id)[0]["confirmed"] is True


def test_sqlite_store_skips_pending_revision_without_lexicon_write(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    run_agent_translation(
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
    event_id = int(store.list_revision_events(confirmed=False)[0]["id"])

    assert store.skip_revision_event_by_id(event_id) is True

    assert store.list_revision_events(confirmed=False) == []
    assert store.find_lexicon_entry("western_myth", "terms", "Leviathan") is None


def test_sqlite_store_marks_pending_revision_special_before_confirmation(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    run_agent_translation(
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
    event_id = int(store.list_revision_events(confirmed=False)[0]["id"])

    assert store.mark_revision_event_special_by_id(event_id) is True

    pending = store.list_revision_events(confirmed=False)
    assert pending[0]["is_special"] is True
    assert store.confirm_revision_event_by_id(event_id) is True
    entries = store.export_topic_entries("western_myth")
    confirmed = [entry for entry in entries["terms"] if entry["source"] == "Leviathan"][0]
    assert confirmed["is_special"] is True

def test_sqlite_store_records_user_correction_metadata_before_lexicon_write(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    result = run_agent_translation(
        text="Leviathan wakes",
        source_lang="en",
        target_lang="zh",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "rough output", confidence=0.66)],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
    )

    event_id = store.record_user_correction(
        run_id=result.contract.run_id,
        topic="western_myth",
        source="Leviathan wakes",
        provisional_text="rough output",
        revised_text="Liweitan awakens from the abyss",
    )

    pending = store.list_revision_events(confirmed=False, run_id=result.contract.run_id)
    correction = [event for event in pending if event["id"] == event_id][0]

    assert correction["update_source"] == "user_correction"
    assert correction["confidence"] == 1.0
    assert correction["is_special"] is True
    assert "diff_ratio=" in correction["note"]
    assert store.find_lexicon_entry("western_myth", "terms", "Leviathan wakes") is None

    assert store.confirm_revision_event_by_id(event_id) is True
    assert store.find_lexicon_entry(
        "western_myth",
        "terms",
        "Leviathan wakes",
    ) == "Liweitan awakens from the abyss"
    entries = store.export_topic_entries("western_myth")
    confirmed = [
        entry for entry in entries["terms"] if entry["source"] == "Leviathan wakes"
    ][0]
    assert confirmed["confirmed_by_user"] is True
    assert confirmed["is_special"] is True
    assert confirmed["source"] == "Leviathan wakes"
    assert confirmed["target"] == "Liweitan awakens from the abyss"


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


def test_sqlite_store_does_not_reconfirm_finalized_agent_run(tmp_path):
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

    assert store.confirm_agent_run(result.contract.run_id) is True
    assert store.confirm_agent_run(result.contract.run_id) is False


def test_sqlite_store_rejects_agent_run_status(tmp_path):
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
    rejected = store.reject_agent_run(result.contract.run_id)
    after = store.get_agent_run(result.contract.run_id)

    assert before is not None
    assert before["status"] == "awaiting_human_confirmation"
    assert rejected is True
    assert after is not None
    assert after["status"] == "rejected"
    assert store.reject_agent_run("missing-run") is False


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
        providers=[StaticModelProvider("local-a", "浣犲ソ", confidence=0.7)],
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
            "浣犲ソ",
        )
    ]
    assert revision_rows == [
        (result.contract.run_id, "terms", "hello", "浣犲ソ", 0)
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
        providers=[StaticModelProvider("local-a", "Liweitan", confidence=0.8)],
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

    assert terms_after_confirm == [("western_myth", "Leviathan", "Liweitan")]
    assert confirmed_flags == [(1,)]


def test_sqlite_store_exports_and_imports_full_lexicon_metadata(tmp_path):
    source_store = AgentRunStore(tmp_path / "source.sqlite3")
    source_store.upsert_lexicon_entry(
        "western_myth",
        "terms",
        "Leviathan",
        "Liweitan",
        note="abyssal proper noun",
        confidence=0.91,
        entry_source="user_correction",
        confirmed_by_user=True,
        is_special=True,
    )
    source_store.upsert_lexicon_entry(
        "sci_fi",
        "phrases",
        "event horizon",
        "shijie xian",
        note="physics phrase",
        confidence=0.72,
        entry_source="agent_proposal",
        confirmed_by_user=False,
        is_special=False,
    )

    exported = source_store.export_all_lexicon_entries()

    assert exported["western_myth"]["terms"]["Leviathan"] == {
        "target": "Liweitan",
        "note": "abyssal proper noun",
        "confidence": 0.91,
        "entry_source": "user_correction",
        "confirmed_by_user": True,
        "is_special": True,
        "created_at": exported["western_myth"]["terms"]["Leviathan"]["created_at"],
        "updated_at": exported["western_myth"]["terms"]["Leviathan"]["updated_at"],
    }

    json_path = tmp_path / "lexicon-export.json"
    json_path.write_text(json.dumps(exported, ensure_ascii=False), encoding="utf-8")
    imported_store = AgentRunStore(tmp_path / "imported.sqlite3")

    imported = imported_store.import_json_lexicon(json_path)

    assert imported == {"terms": 1, "phrases": 1, "style_rules": 0}
    imported_entries = imported_store.export_all_lexicon_entries()
    leviathan = imported_entries["western_myth"]["terms"]["Leviathan"]
    assert leviathan["target"] == "Liweitan"
    assert leviathan["note"] == "abyssal proper noun"
    assert leviathan["confidence"] == 0.91
    assert leviathan["entry_source"] == "user_correction"
    assert leviathan["confirmed_by_user"] is True
    assert leviathan["is_special"] is True
    assert imported_entries["sci_fi"]["phrases"]["event horizon"]["confirmed_by_user"] is False


def test_sqlite_store_persists_only_explicit_translation_rating(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    result = run_agent_translation(
        text="Leviathan wakes",
        source_lang="en",
        target_lang="zh",
        topic="western_myth",
        mode=AgentMode.LEARNING,
        providers=[StaticModelProvider("local-a", "利维坦苏醒", confidence=0.78)],
        api_enabled=False,
        budget_limit=0.0,
        store=store,
    )

    assert store.skip_translation_rating(result.contract.run_id) is None
    assert store.list_translation_ratings() == []

    rating = store.record_translation_rating(
        TranslationRatingSubmission(
            task_id="task-1",
            workflow_run_id=result.contract.run_id,
            mode="learning",
            source_language="en",
            target_language="zh",
            topic="western_myth",
            rating=2,
            issue_tags=("terminology_error", "style_mismatch"),
            dimension_scores={"adequacy": 0.4, "terminology": 0.2},
            comment="term is wrong",
            mdwc_snapshot={"finalScore": result.decision.final_score},
            provider_snapshot=[
                {
                    "providerId": "local-a",
                    "confidence": 0.78,
                    "finalScore": result.decision.final_score,
                }
            ],
            source_text="Leviathan wakes",
            final_translation="利维坦苏醒",
        )
    )

    records = store.list_translation_ratings()

    assert rating.rating == 2
    assert len(records) == 1
    assert records[0]["workflowRunId"] == result.contract.run_id
    assert records[0]["sourceTextHash"]
    assert records[0]["finalTranslationHash"]
    assert "Leviathan wakes" not in json.dumps(records[0], ensure_ascii=False)
    assert "利维坦苏醒" not in json.dumps(records[0], ensure_ascii=False)
    assert records[0]["issueTags"] == ["terminology_error", "style_mismatch"]


def test_rating_feedback_summary_updates_provider_topic_and_mdwc_signals(tmp_path):
    store = AgentRunStore(tmp_path / "agent-runs.sqlite3")
    for index, rating in enumerate((1, 2, 5), start=1):
        store.record_translation_rating(
            TranslationRatingSubmission(
                task_id=f"task-{index}",
                workflow_run_id=f"run-{index}",
                mode="learning",
                source_language="en",
                target_language="zh",
                topic="western_myth",
                rating=rating,
                issue_tags=("terminology_error",) if rating <= 2 else (),
                mdwc_snapshot={"finalScore": 0.88 if rating <= 2 else 0.7},
                provider_snapshot=[
                    {"providerId": "local-a", "confidence": 0.7},
                    {"providerId": "local-b", "confidence": 0.6},
                ],
                source_text=f"source {index}",
                final_translation=f"target {index}",
            )
        )

    summary = store.rating_signal_summary(
        topic="western_myth",
        source_language="en",
        target_language="zh",
        mode="learning",
        provider_ids=("local-a", "local-b"),
    )

    assert summary.sample_count == 3
    assert summary.topic_average_rating == 8 / 3
    assert summary.language_pair_average_rating == 8 / 3
    assert summary.provider_average_rating == 8 / 3
    assert summary.recent_low_rating_count == 2
    assert summary.terminology_issue_ratio == 2 / 3
    assert summary.mdwc_user_mismatch_rate == 2 / 3
    assert summary.low_rating_penalty > 0.0
    assert summary.high_rating_boost > 0.0
