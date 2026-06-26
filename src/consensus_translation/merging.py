from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MergeResult:
    final_text: str
    decision_reason: str
    merge_trace: list[dict[str, object]]


def split_sentences(text: str) -> list[str]:
    chunks = [part for part in re.split(r"(?<=[。！？.!?])", text) if part and part.strip()]
    return chunks


def sentence_overlap(a: str, b: str) -> float:
    left = set(a.strip())
    right = set(b.strip())
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def merge_sentences(a_text: str, b_text: str, a_conf: float, b_conf: float) -> MergeResult:
    a_sentences = split_sentences(a_text)
    b_sentences = split_sentences(b_text)
    max_len = max(len(a_sentences), len(b_sentences))

    merged: list[str] = []
    trace: list[dict[str, object]] = []
    saw_pair = False
    saw_left_only = False
    saw_right_only = False

    for idx in range(max_len):
        left = a_sentences[idx] if idx < len(a_sentences) else ""
        right = b_sentences[idx] if idx < len(b_sentences) else ""

        if left and right:
            saw_pair = True
            overlap = sentence_overlap(left, right)
            if overlap >= 0.5:
                chosen = left if a_conf >= b_conf else right
                why = "consensus-higher-confidence"
            else:
                chosen = left if a_conf >= b_conf else right
                why = "low-overlap-fallback-confidence"
        elif left:
            saw_left_only = True
            chosen = left
            why = "left-only"
        else:
            saw_right_only = True
            chosen = right
            why = "right-only"

        merged.append(chosen)
        trace.append({"sentence_index": idx, "chosen": chosen, "reason": why})

    if saw_pair and (saw_left_only or saw_right_only):
        decision_reason = "sentence-merge-mixed"
    elif saw_pair:
        decision_reason = "sentence-merge-consensus"
    elif saw_left_only and not saw_right_only:
        decision_reason = "sentence-merge-fallback-a"
    elif saw_right_only and not saw_left_only:
        decision_reason = "sentence-merge-fallback-b"
    else:
        decision_reason = "sentence-merge-consensus"

    return MergeResult(final_text="".join(merged).strip(), decision_reason=decision_reason, merge_trace=trace)
