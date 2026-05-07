# Pre-Release Consistency And UI Chinese Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete pre-release consistency cleanup and localize Streamlit UI copy to Chinese without changing backend contract keys or workflow interfaces.

**Architecture:** Keep backend payload and `PAGE_FIELD_MAP` keys unchanged, and apply localization only to Streamlit presentation strings in `app.py`. Add tests to enforce Chinese UI labels while preserving UI/backend mapping behavior. Update worklog and user manual to reflect the final release-consistent state.

**Tech Stack:** Python 3.13, Streamlit, pytest

---

## File Structure Map

- Modify: `app.py` - Chinese UI labels and page display mapping (display-only)
- Modify: `tests/test_ui_contract_mapping.py` - tests for Chinese UI labels while preserving contract key mapping
- Modify: `docs/worklog_zh.md` - release preflight consistency record
- Modify: `docs/user_manual_zh.md` - clarify Chinese UI copy with English contract keys
- Optional Modify: `README.md` - one-line consistency note only if needed after doc updates

### Task 1: Lock UI Localization Contract With Tests

**Files:**
- Modify: `tests/test_ui_contract_mapping.py`
- Modify: `app.py`

- [ ] **Step 1: Write the failing tests for Chinese UI labels and stable page keys**

```python
# tests/test_ui_contract_mapping.py
from app import PAGE_FIELD_MAP, PAGE_LABEL_MAP


def test_page_field_map_keys_remain_contract_stable():
    assert list(PAGE_FIELD_MAP.keys()) == [
        "config",
        "monitor",
        "compare",
        "mdwc",
        "revision",
        "pretrain_report",
    ]


def test_page_label_map_uses_chinese_labels_only():
    assert PAGE_LABEL_MAP == {
        "config": "任务配置",
        "monitor": "执行监控",
        "compare": "候选对比",
        "mdwc": "MDWC 裁决",
        "revision": "修订回写",
        "pretrain_report": "预训练报告",
    }
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_ui_contract_mapping.py::test_page_label_map_uses_chinese_labels_only -v`  
Expected: FAIL with import error for missing `PAGE_LABEL_MAP`

- [ ] **Step 3: Implement minimal UI display-label localization**

```python
# app.py
PAGE_LABEL_MAP: dict[str, str] = {
    "config": "任务配置",
    "monitor": "执行监控",
    "compare": "候选对比",
    "mdwc": "MDWC 裁决",
    "revision": "修订回写",
    "pretrain_report": "预训练报告",
}

st.set_page_config(page_title="共识翻译 V1", layout="wide")
st.title("共识翻译 V1")
st.sidebar.header("任务执行")
source_lang = st.sidebar.text_input("源语言", value="zh")
target_lang = st.sidebar.text_input("目标语言", value="ja")
topic = st.sidebar.text_input("主题", value="general")
local_text = st.sidebar.text_area("本地翻译文本", value="你好")
train_text = st.sidebar.text_area("预训练文本", value="车站")
validation_text = st.sidebar.text_area("验证文本", value="列车")

selected_label = st.sidebar.selectbox("页面", [PAGE_LABEL_MAP[k] for k in PAGE_FIELD_MAP.keys()])
label_to_key = {v: k for k, v in PAGE_LABEL_MAP.items()}
page = label_to_key[selected_label]
st.subheader(PAGE_LABEL_MAP[page])
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_ui_contract_mapping.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_contract_mapping.py
git commit -m "feat: localize streamlit ui copy to chinese labels"
```

### Task 2: Finalize Pre-Release Consistency Documentation

**Files:**
- Modify: `docs/worklog_zh.md`
- Modify: `docs/user_manual_zh.md`

- [ ] **Step 1: Write failing docs consistency tests (lightweight content checks)**

```python
# tests/test_app_bootstrap.py (append)
from pathlib import Path


def test_worklog_mentions_pre_release_ui_zh_consistency():
    text = Path("docs/worklog_zh.md").read_text(encoding="utf-8")
    assert "发布前一致性扫尾" in text
    assert "UI 中文化" in text


def test_user_manual_clarifies_ui_zh_and_contract_keys_english():
    text = Path("docs/user_manual_zh.md").read_text(encoding="utf-8")
    assert "中文文案" in text
    assert "字段键" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_app_bootstrap.py::test_worklog_mentions_pre_release_ui_zh_consistency tests/test_app_bootstrap.py::test_user_manual_clarifies_ui_zh_and_contract_keys_english -v`  
Expected: FAIL until docs are updated

- [ ] **Step 3: Update worklog and user manual with release-consistent wording**

```markdown
<!-- docs/worklog_zh.md add section -->
## 七、发布前一致性扫尾（2026-05-07）

- 完成 UI 中文化（仅展示层文案，不改后端字段键）
- 完成 UI/后端映射核验与全量回归
```

```markdown
<!-- docs/user_manual_zh.md add note -->
注：当前 UI 交互文案为中文；为保持契约稳定性，运行态字段键和后端契约字段仍保持英文命名。
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_app_bootstrap.py::test_worklog_mentions_pre_release_ui_zh_consistency tests/test_app_bootstrap.py::test_user_manual_clarifies_ui_zh_and_contract_keys_english -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs/worklog_zh.md docs/user_manual_zh.md tests/test_app_bootstrap.py
git commit -m "docs: finalize pre-release consistency and ui zh notes"
```

### Task 3: Verification Gate And Release-Safe Wrap-Up

**Files:**
- Modify: `docs/worklog_zh.md`
- Optional Modify: `README.md`

- [ ] **Step 1: Run UI/backend mapping verification**

Run: `pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`  
Expected: PASS

- [ ] **Step 2: Run full regression suite**

Run: `pytest -q`  
Expected: PASS (no new failures)

- [ ] **Step 3: Run manual startup check for Chinese UI labels**

Run: `powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1`  
Expected: startup success with `deps-ok`; UI labels visible in Chinese

- [ ] **Step 4: Record final verification evidence in worklog**

```markdown
<!-- docs/worklog_zh.md append evidence bullets -->
- UI/后端映射核验：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py` 通过
- 全量回归：`pytest -q` 通过
- 手动启动检查：中文 UI 文案显示正确
```

- [ ] **Step 5: Commit**

```bash
git add docs/worklog_zh.md README.md
git commit -m "docs: append pre-release verification evidence"
```

## Self-Review Checklist

- Spec coverage:
  - UI 文案中文化（展示层） -> Task 1
  - 不改 PAGE_FIELD_MAP key / 后端契约字段 -> Task 1 tests + implementation
  - 发布前一致性文档收口 -> Task 2 + Task 3
  - 核验命令与证据 -> Task 3
- Placeholder scan: no `TODO`, `TBD`, or unresolved placeholders
- Type consistency:
  - `PAGE_FIELD_MAP` keys remain unchanged
  - `PAGE_LABEL_MAP` only controls display labels
  - `extract_page_data` and workflow payload contract unchanged
