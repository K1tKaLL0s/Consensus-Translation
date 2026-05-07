# UI Input Restructure And Sidebar State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Streamlit UI to use language selectors, topic select+input override, three fused input areas (manual or upload), and move all status/details to a collapsed sidebar area while keeping main area result-only.

**Architecture:** Keep backend contracts and workflow interfaces unchanged. Implement all behavioral changes in `app.py` with targeted helper functions and tests in `tests/test_ui_contract_mapping.py`. Update docs to match new interaction rules and evidence.

**Tech Stack:** Python 3.13, Streamlit, python-docx, pytest

---

## File Structure Map

- Modify: `app.py` - UI layout, language selectors, topic resolver, fused input controls, sidebar state expander
- Modify: `tests/test_ui_contract_mapping.py` - behavioral tests for new UI state and helper logic
- Modify: `docs/user_manual_zh.md` - user-facing behavior updates
- Modify: `docs/worklog_zh.md` - verification evidence and release notes

### Task 1: Add Tests For New Input/Topic/Sidebar Rules

**Files:**
- Modify: `tests/test_ui_contract_mapping.py`

- [ ] **Step 1: Write failing tests for language options, topic override, and result-only main rendering helpers**

```python
# tests/test_ui_contract_mapping.py
from app import LANGUAGE_OPTIONS, resolve_topic_value, build_sidebar_detail_payload


def test_language_options_are_fixed_three_codes():
    assert LANGUAGE_OPTIONS == ["zh", "en", "ja"]


def test_topic_manual_input_overrides_selected_topic():
    topic = resolve_topic_value(selected_topic="history", manual_topic="my_new_topic")
    assert topic == "my_new_topic"


def test_topic_selected_used_when_manual_blank():
    topic = resolve_topic_value(selected_topic="history", manual_topic="   ")
    assert topic == "history"


def test_sidebar_detail_payload_contains_page_and_status_fields():
    detail = build_sidebar_detail_payload(page_key="monitor", page_data={"stage_status.current": "finalize"}, latest_payload={"mode": "local"})
    assert detail["page_key"] == "monitor"
    assert detail["page_data"]["stage_status.current"] == "finalize"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `E:\Ana\python.exe -m pytest tests/test_ui_contract_mapping.py::test_language_options_are_fixed_three_codes tests/test_ui_contract_mapping.py::test_topic_manual_input_overrides_selected_topic -v`  
Expected: FAIL for missing symbols/helpers

- [ ] **Step 3: Commit only tests after failing run evidence in notes**

```bash
git add tests/test_ui_contract_mapping.py
git commit -m "test: add ui restructure behavior tests" 
```

### Task 2: Implement UI Restructure In app.py

**Files:**
- Modify: `app.py`
- Modify: `tests/test_ui_contract_mapping.py`

- [ ] **Step 1: Implement language selectors and topic resolver**

```python
# app.py
LANGUAGE_OPTIONS = ["zh", "en", "ja"]


def resolve_topic_value(selected_topic: str, manual_topic: str) -> str:
    text = manual_topic.strip()
    if text:
        return text
    return selected_topic
```

- [ ] **Step 2: Implement three fused input controls (manual + upload) with independent state**

```python
# app.py (inside main)
local_upload = st.sidebar.file_uploader("本地任务上传（txt/md/docx）", type=["txt", "md", "docx"], key="local_upload")
pretrain_upload = st.sidebar.file_uploader("预训练文本上传（txt/md/docx）", type=["txt", "md", "docx"], key="pretrain_upload")
validation_upload = st.sidebar.file_uploader("验证文本上传（txt/md/docx）", type=["txt", "md", "docx"], key="validation_upload")

local_uploaded_text, local_meta = extract_uploaded_text(local_upload)
pretrain_uploaded_text, pretrain_meta = extract_uploaded_text(pretrain_upload)
validation_uploaded_text, validation_meta = extract_uploaded_text(validation_upload)
```

- [ ] **Step 3: Move details into collapsed sidebar expander and keep main as result-only**

```python
# app.py
def build_sidebar_detail_payload(page_key: str, page_data: dict[str, object], latest_payload: dict[str, object]) -> dict[str, object]:
    return {
        "page_key": page_key,
        "page_data": page_data,
        "latest_payload_mode": latest_payload.get("mode"),
        "latest_payload_contract": latest_payload.get("contract"),
    }


# main rendering
with st.sidebar.expander("运行状态与明细", expanded=False):
    st.json(build_sidebar_detail_payload(page, page_data, latest_payload))

st.subheader("翻译结果")
st.json(build_result_panel(latest_payload))
```

- [ ] **Step 4: Run UI tests and targeted workflow compatibility tests**

Run: `E:\Ana\python.exe -m pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`  
Expected: PASS

- [ ] **Step 5: Commit implementation**

```bash
git add app.py tests/test_ui_contract_mapping.py
git commit -m "feat: restructure ui inputs and move detail state to collapsed sidebar"
```

### Task 3: Docs Sync And Full Verification

**Files:**
- Modify: `docs/user_manual_zh.md`
- Modify: `docs/worklog_zh.md`

- [ ] **Step 1: Update user manual with new UI interaction rules**

```markdown
<!-- docs/user_manual_zh.md -->
- 源语言/目标语言改为下拉选择（zh/en/ja）。
- 主题支持“下拉选择 + 新主题输入覆盖”。
- 本地文本、预训练文本、验证文本均支持“手输或上传”。
- 主区仅显示“翻译结果”，其余状态在侧栏“运行状态与明细”（默认收起）。
```

- [ ] **Step 2: Record verification evidence in worklog**

```markdown
<!-- docs/worklog_zh.md -->
- UI 重构核验：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py` 通过。
- 全量回归：`pytest -q` 通过。
- 手工检查：语言选择、主题覆盖、三输入融合、侧栏收敛均符合预期。
```

- [ ] **Step 3: Run full regression**

Run: `E:\Ana\python.exe -m pytest -q`  
Expected: PASS

- [ ] **Step 4: Commit docs and evidence**

```bash
git add docs/user_manual_zh.md docs/worklog_zh.md
git commit -m "docs: sync ui restructure behavior and verification evidence"
```

## Self-Review Checklist

- Spec coverage:
  - Language selectbox (`zh/en/ja`) -> Task 1/2
  - Topic select + manual override -> Task 1/2
  - Three fused input zones -> Task 2
  - Main result-only + sidebar collapsed details -> Task 2
  - Regression + docs sync -> Task 3
- Placeholder scan: no TODO/TBD placeholders
- Type consistency:
  - `PAGE_FIELD_MAP` keys unchanged
  - backend workflow signatures unchanged
  - new helper names used consistently in tests and implementation
