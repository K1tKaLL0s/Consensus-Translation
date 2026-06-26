from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.merging import merge_sentences, sentence_overlap, split_sentences


def test_split_sentences_keeps_cjk_and_ascii_boundaries():
    text = "第一句。Second sentence!第三句？"
    assert split_sentences(text) == ["第一句。", "Second sentence!", "第三句？"]


def test_sentence_overlap_returns_zero_for_empty_pair():
    assert sentence_overlap("", "") == 0.0


def test_merge_sentences_prefers_consensus_when_overlap_high():
    result = merge_sentences(
        a_text="駅へ行く。ありがとう。",
        b_text="駅へ行く。どうも。",
        a_conf=0.62,
        b_conf=0.70,
    )
    assert result.final_text == "駅へ行く。どうも。"
    assert result.decision_reason == "sentence-merge-consensus"
    assert result.merge_trace == [
        {
            "sentence_index": 0,
            "chosen": "駅へ行く。",
            "reason": "consensus-higher-confidence",
        },
        {
            "sentence_index": 1,
            "chosen": "どうも。",
            "reason": "low-overlap-fallback-confidence",
        },
    ]


def test_merge_sentences_falls_back_to_higher_confidence_for_remaining_sentence():
    result = merge_sentences(
        a_text="A one. A two.",
        b_text="B one.",
        a_conf=0.75,
        b_conf=0.60,
    )
    assert result.final_text == "A one. A two."
    assert result.decision_reason == "sentence-merge-mixed"
    assert result.merge_trace == [
        {
            "sentence_index": 0,
            "chosen": "A one.",
            "reason": "consensus-higher-confidence",
        },
        {
            "sentence_index": 1,
            "chosen": " A two.",
            "reason": "left-only",
        },
    ]
