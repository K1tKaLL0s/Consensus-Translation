from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.lexicon import LexiconRepo, RevisionPayload


def test_revision_updates_themed_lexicon_entry():
    repo = LexiconRepo()
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


def test_large_diff_marks_special_and_lowers_weight():
    repo = LexiconRepo()
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
