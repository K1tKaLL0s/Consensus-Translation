from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.lexicon import LexiconRepo, RevisionPayload


def test_revision_updates_themed_lexicon_entry(tmp_path):
    repo = LexiconRepo(store_path=tmp_path / "lexicon.json")
    payload = RevisionPayload(
        topic="travel",
        source="车站",
        target="駅",
        diff_ratio=0.2,
    )

    event = repo.apply_revision(payload)

    assert repo.find("travel", "车站") == "駅"
    assert event.special_flag is False
    assert event.user_prior_delta == 0.05


def test_large_diff_marks_special_and_lowers_weight(tmp_path):
    repo = LexiconRepo(store_path=tmp_path / "lexicon.json")
    payload = RevisionPayload(
        topic=None,
        source="你好",
        target="今日は",
        diff_ratio=0.8,
    )

    event = repo.apply_revision(payload)

    assert repo.find("uncategorized", "你好") == "今日は"
    assert event.special_flag is True
    assert event.user_prior_delta == -0.1


def test_lexicon_persists_across_instances(tmp_path):
    store_file = tmp_path / "lexicon.json"
    first = LexiconRepo(store_path=store_file)
    first.apply_revision(
        RevisionPayload(
            topic="travel",
            source="车站",
            target="駅",
            diff_ratio=0.2,
        )
    )

    second = LexiconRepo(store_path=store_file)
    assert second.find("travel", "车站") == "駅"


def test_default_store_path_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    repo = LexiconRepo()

    assert str(repo._store_path).startswith(str(tmp_path))
    assert repo._store_path.name == "lexicon.json"


def test_apply_revision_writes_schema_v2_layers(tmp_path):
    store_file = tmp_path / "lexicon.json"
    repo = LexiconRepo(store_path=store_file)

    repo.apply_revision(
        RevisionPayload(
            topic="travel",
            source="车站",
            target="駅",
            diff_ratio=0.1,
        )
    )

    data = json.loads(store_file.read_text(encoding="utf-8"))
    assert data["travel"]["terms"]["车站"] == "駅"
    assert data["travel"]["phrases"] == {}
    assert data["travel"]["style_rules"] == {}


def test_export_topic_returns_full_three_layer_payload(tmp_path):
    repo = LexiconRepo(store_path=tmp_path / "lexicon.json")
    repo.apply_revision(
        RevisionPayload(
            topic="travel",
            source="车站",
            target="駅",
            diff_ratio=0.1,
        )
    )

    exported = repo.export_topic("travel")

    assert exported == {
        "terms": {"车站": "駅"},
        "phrases": {},
        "style_rules": {},
    }


def test_load_v1_flat_schema_migrates_entries_into_terms(tmp_path):
    store_file = tmp_path / "lexicon.json"
    store_file.write_text(
        json.dumps({"travel": {"车站": "駅", "机场": "空港"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    repo = LexiconRepo(store_path=store_file)

    assert repo.export_topic("travel") == {
        "terms": {"车站": "駅", "机场": "空港"},
        "phrases": {},
        "style_rules": {},
    }


def test_load_partial_v2_schema_preserves_terms_layer_data(tmp_path):
    store_file = tmp_path / "lexicon.json"
    store_file.write_text(
        json.dumps(
            {
                "travel": {
                    "terms": {"车站": "駅"},
                    "unrelated": "kept out of layered data",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    repo = LexiconRepo(store_path=store_file)

    assert repo.find("travel", "车站") == "駅"
    assert repo.export_topic("travel") == {
        "terms": {"车站": "駅"},
        "phrases": {},
        "style_rules": {},
    }


def test_load_partial_v2_filters_malformed_layer_values_safely(tmp_path):
    store_file = tmp_path / "lexicon.json"
    store_file.write_text(
        json.dumps(
                {
                    "travel": {
                        "terms": ["not", "a", "dict"],
                        "phrases": {"greeting": "こんにちは", "bad_num": 123, "bad_null": None},
                        "style_rules": {"formal": "丁寧", "bad": None},
                        "车站": "駅",
                    }
                },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    repo = LexiconRepo(store_path=store_file)

    assert repo.export_topic("travel") == {
        "terms": {},
        "phrases": {"greeting": "こんにちは"},
        "style_rules": {"formal": "丁寧"},
    }
