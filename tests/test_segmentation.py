from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from consensus_translation.segmentation import build_hierarchy


def test_build_hierarchy_creates_token_sentence_segment_links():
    text = "alpha beta，gamma。delta epsilon。"

    tree = build_hierarchy(text)

    assert [segment.id for segment in tree.segments] == ["seg-1", "seg-2"]
    assert [segment.text for segment in tree.segments] == [
        "alpha beta，gamma",
        "delta epsilon",
    ]

    assert [sentence.id for sentence in tree.sentences] == ["sent-1", "sent-2"]
    assert [sentence.segment_id for sentence in tree.sentences] == ["seg-1", "seg-2"]
    assert [sentence.text for sentence in tree.sentences] == [
        "alpha beta，gamma",
        "delta epsilon",
    ]

    token_texts_by_sentence = {}
    for token in tree.tokens:
        token_texts_by_sentence.setdefault(token.sentence_id, []).append(token.text)

    assert token_texts_by_sentence == {
        "sent-1": ["alpha", "beta", "gamma"],
        "sent-2": ["delta", "epsilon"],
    }
    assert all(token.priority_term is False for token in tree.tokens)


def test_build_hierarchy_marks_domain_terms_as_priority_tokens():
    text = "translation memory improves quality。alpha beta。"
    domain_terms = {"translation", "translation memory", "beta"}

    tree = build_hierarchy(text, domain_terms=domain_terms)

    token_pairs = {(token.sentence_id, token.text): token for token in tree.tokens}

    assert token_pairs[("sent-1", "translation")].priority_term is True
    assert token_pairs[("sent-2", "beta")].priority_term is True

    phrase_tokens = [
        token
        for token in tree.tokens
        if token.sentence_id == "sent-1" and token.text == "translation memory"
    ]
    assert len(phrase_tokens) == 1
    assert phrase_tokens[0].priority_term is True


def test_build_hierarchy_inserts_phrase_terms_in_deterministic_order_with_stable_ids():
    text = "machine translation memory improves machine translation quality。"
    domain_terms = {
        "machine translation",
        "translation memory",
        "machine translation memory",
    }

    tree = build_hierarchy(text, domain_terms=domain_terms)

    phrase_tokens = [token for token in tree.tokens if " " in token.text]
    assert [(token.id, token.text) for token in phrase_tokens] == [
        ("tok-8", "machine translation memory"),
        ("tok-9", "machine translation"),
        ("tok-10", "translation memory"),
    ]
