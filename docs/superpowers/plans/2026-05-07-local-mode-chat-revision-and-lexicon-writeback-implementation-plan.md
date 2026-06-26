# Local Mode Chat Revision And Lexicon Writeback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make local translation robust to single-engine failures, produce sentence-level merged output, and ship the confirm/revise chat flow where only revise triggers lexicon writeback.

**Architecture:** Add a dedicated merge module for sentence-level decisions, then update local workflow to collect engine errors and degrade safely. Keep UI/backend contract keys stable while changing the main panel to chat-only output with explicit `确认`/`修正` branching. Implement local revision writeback as a workflow helper so UI stays thin.

**Tech Stack:** Python 3.13, Streamlit, pytest

---

## File Structure Map

- Create: `src/consensus_translation/merging.py` - sentence split/overlap/merge logic and trace output
- Modify: `src/consensus_translation/workflows.py` - resilient engine execution, merge integration, local revision writeback
- Modify: `app.py` - chat-only result panel and `确认/修正` interaction flow
- Create: `tests/test_merging.py` - merge behavior unit tests
- Modify: `tests/test_workflows.py` - resilient workflow and local revision writeback tests
- Modify: `tests/test_ui_contract_mapping.py` - UI helper behavior for confirm/revise branch control
- Modify: `docs/user_manual_zh.md` - chat output and confirm/revise behavior note
- Modify: `docs/worklog_zh.md` - implementation verification evidence

### Task 1: Build sentence-level merge module with TDD

**Files:**
- Create: `tests/test_merging.py`
- Create: `src/consensus_translation/merging.py`

- [ ] **Step 1: Write failing tests for sentence split and merge behavior**

```python
# tests/test_merging.py
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
    assert result.final_text.startswith("駅へ行く。")
    assert result.decision_reason == "sentence-merge-consensus"
    assert len(result.merge_trace) == 2


def test_merge_sentences_falls_back_to_higher_confidence_for_remaining_sentence():
    result = merge_sentences(
        a_text="A one. A two.",
        b_text="B one.",
        a_conf=0.75,
        b_conf=0.60,
    )
    assert result.final_text.endswith("A two.")
```

- [ ] **Step 2: Run tests to verify RED state**

Run: `pytest tests/test_merging.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'consensus_translation.merging'`

- [ ] **Step 3: Implement minimal merge module to satisfy tests**

```python
# src/consensus_translation/merging.py
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
    return [chunk.strip() for chunk in chunks]


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
    reason = "sentence-merge-consensus"

    for idx in range(max_len):
        left = a_sentences[idx] if idx < len(a_sentences) else ""
        right = b_sentences[idx] if idx < len(b_sentences) else ""

        if left and right:
            overlap = sentence_overlap(left, right)
            if overlap >= 0.5:
                chosen = left if a_conf >= b_conf else right
                why = "consensus-higher-confidence"
            else:
                chosen = left if a_conf >= b_conf else right
                why = "low-overlap-fallback-confidence"
                reason = "sentence-merge-fallback-a" if chosen == left else "sentence-merge-fallback-b"
        elif left:
            chosen = left
            why = "left-only"
            reason = "sentence-merge-fallback-a"
        else:
            chosen = right
            why = "right-only"
            reason = "sentence-merge-fallback-b"

        merged.append(chosen)
        trace.append({"sentence_index": idx, "chosen": chosen, "reason": why})

    return MergeResult(final_text="".join(merged).strip(), decision_reason=reason, merge_trace=trace)
```

- [ ] **Step 4: Run tests to verify GREEN state**

Run: `pytest tests/test_merging.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_merging.py src/consensus_translation/merging.py
git commit -m "feat: add sentence-level merge module"
```

### Task 2: Add resilient local workflow and local revision writeback

**Files:**
- Modify: `src/consensus_translation/workflows.py`
- Modify: `tests/test_workflows.py`

- [ ] **Step 1: Write failing tests for single-engine fallback and local writeback**

```python
# tests/test_workflows.py (append)
from consensus_translation.lexicon import LexiconRepo
from consensus_translation.workflows import apply_local_revision, run_local_job


def test_local_job_survives_engine_a_index_error(monkeypatch):
    def boom(*_args, **_kwargs):
        raise IndexError("index out of range in self")

    monkeypatch.setattr("consensus_translation.workflows.LocalEngineA.translate", boom)
    monkeypatch.setattr(
        "consensus_translation.workflows.LocalEngineB.translate",
        lambda _self, _text, _source, _target: ("生き残り", 0.71),
    )

    result = run_local_job("你好", "zh", "ja", "general")

    assert result["final_text"] == "生き残り"
    assert result["decision_reason"] == "engine-single-survivor-b"
    assert "engine_a" in result["engine_errors"]


def test_apply_local_revision_writes_uncategorized_when_topic_missing(tmp_path):
    repo = LexiconRepo(store_path=tmp_path / "lexicon.json")
    result = apply_local_revision(
        source_text="你好",
        provisional_text="こんにちは",
        revised_text="今日は",
        topic="",
        lexicon_repo=repo,
    )

    assert result["update_status"] == "ok"
    assert result["special_flag"] is False
    assert repo.find("uncategorized", "你好") == "今日は"
```

- [ ] **Step 2: Run targeted tests to verify RED state**

Run: `pytest tests/test_workflows.py::test_local_job_survives_engine_a_index_error tests/test_workflows.py::test_apply_local_revision_writes_uncategorized_when_topic_missing -v`  
Expected: FAIL with missing key/function assertions

- [ ] **Step 3: Implement minimal workflow changes for fallback + writeback**

```python
# src/consensus_translation/workflows.py (key additions)
from consensus_translation.merging import merge_sentences


def _safe_translate(engine, engine_name: str, text: str, source_lang: str, target_lang: str):
    try:
        output, conf = engine.translate(text, source_lang, target_lang)
        return {"ok": True, "text": output, "confidence": conf, "error": None}
    except Exception as exc:
        return {"ok": False, "text": None, "confidence": 0.0, "error": f"{engine_name}: {exc}"}


def _diff_ratio(left: str, right: str) -> float:
    left_set = set(left.strip())
    right_set = set(right.strip())
    union = left_set | right_set
    if not union:
        return 0.0
    return 1.0 - (len(left_set & right_set) / len(union))


def apply_local_revision(
    source_text: str,
    provisional_text: str,
    revised_text: str,
    topic: str | None,
    lexicon_repo: LexiconRepo | None = None,
) -> dict[str, object]:
    repo = lexicon_repo or LexiconRepo()
    ratio = _diff_ratio(provisional_text, revised_text)
    event = repo.apply_revision(
        RevisionPayload(
            topic=topic or "uncategorized",
            source=source_text,
            target=revised_text,
            diff_ratio=ratio,
        )
    )
    return {
        "diff_ratio": ratio,
        "special_flag": event.special_flag,
        "update_status": "ok",
        "lexicon_updates": [{"topic": topic or "uncategorized", "special_flag": event.special_flag}],
    }
```

```python
# src/consensus_translation/workflows.py (inside run_local_job engine stage)
engine_a_result = _safe_translate(engine_a, "engine_a", text, source_lang, target_lang)
engine_b_result = _safe_translate(engine_b, "engine_b", text, source_lang, target_lang)

engine_errors: dict[str, str] = {}
if not engine_a_result["ok"]:
    engine_errors["engine_a"] = str(engine_a_result["error"])
if not engine_b_result["ok"]:
    engine_errors["engine_b"] = str(engine_b_result["error"])

if not engine_a_result["ok"] and not engine_b_result["ok"]:
    contract.stage_status.error_code = "ENGINE_FAILURE"
    contract.stage_status.error_message = f"{engine_errors}"
    raise RuntimeError("both engines failed")

if engine_a_result["ok"] and engine_b_result["ok"]:
    merged = merge_sentences(
        str(engine_a_result["text"]),
        str(engine_b_result["text"]),
        float(engine_a_result["confidence"]),
        float(engine_b_result["confidence"]),
    )
    final_text = merged.final_text
    decision_reason = merged.decision_reason
    merge_trace = merged.merge_trace
elif engine_a_result["ok"]:
    final_text = str(engine_a_result["text"])
    decision_reason = "engine-single-survivor-a"
    merge_trace = []
else:
    final_text = str(engine_b_result["text"])
    decision_reason = "engine-single-survivor-b"
    merge_trace = []
```

- [ ] **Step 4: Run targeted tests to verify GREEN state**

Run: `pytest tests/test_workflows.py::test_local_job_survives_engine_a_index_error tests/test_workflows.py::test_apply_local_revision_writes_uncategorized_when_topic_missing -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/consensus_translation/workflows.py tests/test_workflows.py
git commit -m "feat: add resilient local workflow and revision writeback"
```

### Task 3: Switch UI to chat output with confirm/revise gate

**Files:**
- Modify: `app.py`
- Modify: `tests/test_ui_contract_mapping.py`

- [ ] **Step 1: Write failing tests for confirm/revise branch helpers**

```python
# tests/test_ui_contract_mapping.py (append)
from app import decide_final_output_action


def test_decide_final_output_action_confirm_does_not_writeback():
    state = decide_final_output_action(action="confirm", revised_text="", has_provisional=True)
    assert state["finalized"] is True
    assert state["should_writeback"] is False


def test_decide_final_output_action_revise_requires_writeback():
    state = decide_final_output_action(action="revise", revised_text="修正文", has_provisional=True)
    assert state["finalized"] is False
    assert state["should_writeback"] is True
```

- [ ] **Step 2: Run targeted tests to verify RED state**

Run: `pytest tests/test_ui_contract_mapping.py::test_decide_final_output_action_confirm_does_not_writeback tests/test_ui_contract_mapping.py::test_decide_final_output_action_revise_requires_writeback -v`  
Expected: FAIL with `ImportError` for missing helper

- [ ] **Step 3: Implement minimal helper and chat flow changes**

```python
# app.py (new helper)
def decide_final_output_action(action: str, revised_text: str, has_provisional: bool) -> dict[str, object]:
    if not has_provisional:
        return {"finalized": False, "should_writeback": False}
    if action == "confirm":
        return {"finalized": True, "should_writeback": False}
    if action == "revise" and revised_text.strip():
        return {"finalized": False, "should_writeback": True}
    return {"finalized": False, "should_writeback": False}
```

```python
# app.py (main panel pattern)
st.subheader("翻译结果")
provisional_text = str((latest_payload or {}).get("provisional_text") or "")
if provisional_text:
    with st.chat_message("assistant"):
        st.write(provisional_text)
    confirm_clicked = st.button("确认", key="confirm_result")
    revise_clicked = st.button("修正", key="revise_result")

    if confirm_clicked:
        st.session_state["final_output_text"] = provisional_text

    if revise_clicked:
        user_revision = st.chat_input("请输入修正内容")
        if user_revision:
            with st.chat_message("user"):
                st.write(user_revision)
            revision_state = decide_final_output_action("revise", user_revision, True)
            if revision_state["should_writeback"]:
                revision_result = apply_local_revision(
                    source_text=st.session_state.get("last_source_text", ""),
                    provisional_text=provisional_text,
                    revised_text=user_revision,
                    topic=topic,
                )
                st.session_state["revision_state"] = revision_result
                st.session_state["final_output_text"] = user_revision

final_output = st.session_state.get("final_output_text", "")
if final_output:
    with st.chat_message("assistant"):
        st.write(final_output)
```

- [ ] **Step 4: Run targeted tests to verify GREEN state**

Run: `pytest tests/test_ui_contract_mapping.py::test_decide_final_output_action_confirm_does_not_writeback tests/test_ui_contract_mapping.py::test_decide_final_output_action_revise_requires_writeback -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_contract_mapping.py
git commit -m "feat: add confirm-revise chat output flow"
```

### Task 4: Regression verification and documentation sync

**Files:**
- Modify: `docs/user_manual_zh.md`
- Modify: `docs/worklog_zh.md`

- [ ] **Step 1: Add failing docs assertions for new chat and writeback behavior**

```python
# tests/test_app_bootstrap.py (append)
def test_user_manual_mentions_confirm_or_revise_gate():
    root = Path(__file__).resolve().parents[1]
    manual = (root / "docs" / "user_manual_zh.md").read_text(encoding="utf-8")
    assert "确认" in manual
    assert "修正" in manual
    assert "仅在选择修正后触发词库回写" in manual
```

- [ ] **Step 2: Run docs test to verify RED state**

Run: `pytest tests/test_app_bootstrap.py::test_user_manual_mentions_confirm_or_revise_gate -v`  
Expected: FAIL until manual is updated

- [ ] **Step 3: Update docs and record verification evidence**

```markdown
<!-- docs/user_manual_zh.md add under result section -->
- 对话框下提供 `确认` / `修正` 两个动作。
- 选择 `确认`：直接输出最终文本。
- 选择 `修正`：进入用户修正输入，并触发词库回写。
- 词库回写只在 `修正` 分支发生。
```

```markdown
<!-- docs/worklog_zh.md append verification entry -->
- 本地模式新增单引擎降级、句子级融合、确认/修正分支与修正回写闭环。
- 回归命令：`pytest -q` 通过。
```

- [ ] **Step 4: Run full verification suite**

Run: `pytest -q`  
Expected: PASS (all tests green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_app_bootstrap.py docs/user_manual_zh.md docs/worklog_zh.md
git commit -m "docs: align manual and worklog with confirm-revise writeback flow"
```

## Self-Review Checklist

- Spec coverage:
  - 单引擎容错与双引擎失败路径 -> Task 2
  - 句子级融合（重合度+置信度） -> Task 1 + Task 2
  - 主区仅对话框 -> Task 3
  - 确认/修正开关，修正才回写 -> Task 3 + Task 4
  - 本地模式词库回写与特殊标记 -> Task 2
- Placeholder scan: no `TODO`/`TBD`/ambiguous placeholder steps
- Type consistency:
  - `merge_sentences` + `MergeResult` naming consistent across tests and workflow
  - `apply_local_revision` signature consistent between workflow and UI
  - `decide_final_output_action` keys stable: `finalized`, `should_writeback`
