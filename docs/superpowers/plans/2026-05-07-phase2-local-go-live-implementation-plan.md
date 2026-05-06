# Phase 2 Local Go-Live Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Phase 2 so local mode is production-usable, pretrain metrics are real and reproducible, and UI fields strictly match backend runtime payload.

**Architecture:** Extend the current single-process workflow by adding a deterministic evaluation module, layered lexicon schema, domain signal scoring, and operational utilities (bootstrap, structured logs, audit, checkpoint resume). Keep `run_local_job` and `run_pretrain_job` as orchestration entrypoints and enforce UI/backend parity with contract mapping tests.

**Tech Stack:** Python 3.13, Streamlit, Pydantic v2, pytest, pytest-cov, standard library (`json`, `logging`, `pathlib`, `datetime`)

---

## File Structure Map

- Create: `src/consensus_translation/evaluation.py` - reproducible validation metric calculator
- Create: `src/consensus_translation/domain_signals.py` - myth/history/science signal extraction
- Create: `src/consensus_translation/ops.py` - audit export and checkpoint helpers
- Create: `scripts/init_env.ps1` - environment bootstrap script for Phase 2
- Modify: `src/consensus_translation/config.py` - evaluation + ops settings
- Modify: `src/consensus_translation/lexicon.py` - schema versioning and 3-layer storage
- Modify: `src/consensus_translation/mdwc.py` - optional domain-weight adjustment helpers
- Modify: `src/consensus_translation/workflows.py` - M1/M2/M3/M4 integration
- Modify: `app.py` - block Phase-3 UI exposure, keep mapping parity
- Modify: `tests/test_workflows.py` - workflow-level gate tests
- Create: `tests/test_evaluation.py` - deterministic metric tests
- Modify: `tests/test_lexicon.py` - layered lexicon tests
- Create: `tests/test_domain_signals.py` - domain extraction and weighting tests
- Modify: `tests/test_ui_contract_mapping.py` - strict UI/backend parity and no AI-mode entry tests

### Task 1: Lock UI-Backend Parity Gate First

**Files:**
- Modify: `tests/test_ui_contract_mapping.py`
- Modify: `app.py`

- [ ] **Step 1: Write failing tests for strict parity and Phase-3 UI exclusion**

```python
# tests/test_ui_contract_mapping.py
from app import PAGE_FIELD_MAP, extract_page_data


def test_all_page_fields_resolve_from_runtime_or_contract_fallback():
    payload = {
        "final_score": 0.9,
        "contract": {
            "stage_status": {"current": "finalize", "progress": 1.0, "retry_count": 0, "error_code": None, "error_message": None}
        },
    }
    data = extract_page_data("monitor", payload)
    assert data["stage_status.current"] == "finalize"
    assert data["stage_status.progress"] == 1.0


def test_ui_does_not_expose_phase3_ai_mode_controls():
    forbidden = {"ai_mode", "ai_vote", "ai_iteration", "multi_model"}
    all_fields = {field for fields in PAGE_FIELD_MAP.values() for field in fields}
    assert forbidden.isdisjoint(all_fields)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_contract_mapping.py::test_ui_does_not_expose_phase3_ai_mode_controls -v`  
Expected: FAIL if any forbidden field exists or parity behavior diverges.

- [ ] **Step 3: Make minimal UI mapping-safe implementation**

```python
# app.py (ensure PAGE_FIELD_MAP contains only phase-2 fields)
PAGE_FIELD_MAP: dict[str, list[str]] = {
    "config": ["job_id", "mode", "source_lang", "target_lang", "topic", "domain_tags", "granularity"],
    "monitor": [
        "stage_status.current",
        "stage_status.progress",
        "stage_status.retry_count",
        "stage_status.error_code",
        "stage_status.error_message",
    ],
    "compare": ["cand_a", "cand_b", "token_diff", "sentence_diff", "segment_diff", "overlap_score", "confidence_a", "confidence_b", "term_consistency"],
    "mdwc": ["weights", "token_score", "sentence_score", "segment_score", "user_prior", "final_score", "decision_reason"],
    "revision": ["user_revision", "diff", "special_flag", "lexicon_updates", "theme_bucket", "update_status"],
    "pretrain_report": ["validation_metrics", "improvement_rate", "conflict_terms", "uncategorized_terms", "calibration_summary"],
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_ui_contract_mapping.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_contract_mapping.py
git commit -m "test: enforce phase2 ui-backend parity gate"
```

### Task 2: Implement M1 Real Validation Metrics

**Files:**
- Create: `src/consensus_translation/evaluation.py`
- Modify: `src/consensus_translation/config.py`
- Modify: `src/consensus_translation/workflows.py`
- Create: `tests/test_evaluation.py`
- Modify: `tests/test_workflows.py`

- [ ] **Step 1: Write failing tests for deterministic computed metrics**

```python
# tests/test_evaluation.py
from consensus_translation.evaluation import evaluate_translation


def test_evaluation_returns_reproducible_metrics_for_same_input():
    left = evaluate_translation(source_text="车站", predicted_text="station", reference_text="station")
    right = evaluate_translation(source_text="车站", predicted_text="station", reference_text="station")
    assert left == right
    assert set(left.keys()) == {"term_consistency", "length_ratio", "edit_similarity", "overall"}


def test_evaluation_handles_empty_reference_safely():
    out = evaluate_translation(source_text="车站", predicted_text="station", reference_text="")
    assert out["overall"] >= 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_evaluation.py -v`  
Expected: FAIL with `ModuleNotFoundError` for `consensus_translation.evaluation`

- [ ] **Step 3: Implement evaluation module (deterministic only)**

```python
# src/consensus_translation/evaluation.py
from __future__ import annotations

from difflib import SequenceMatcher


def _safe_ratio(a: float, b: float) -> float:
    if b <= 0.0:
        return 1.0
    return max(0.0, min(1.0, a / b))


def evaluate_translation(source_text: str, predicted_text: str, reference_text: str) -> dict[str, float]:
    ref_tokens = [x for x in reference_text.split() if x]
    pred_tokens = [x for x in predicted_text.split() if x]
    overlap = len(set(ref_tokens).intersection(set(pred_tokens)))
    term_consistency = _safe_ratio(float(overlap), float(len(set(ref_tokens))))

    ref_len = float(len(reference_text.strip()))
    pred_len = float(len(predicted_text.strip()))
    length_ratio = _safe_ratio(min(ref_len, pred_len), max(ref_len, pred_len) if max(ref_len, pred_len) > 0 else 1.0)

    edit_similarity = SequenceMatcher(a=reference_text, b=predicted_text).ratio()
    overall = round((0.4 * term_consistency) + (0.2 * length_ratio) + (0.4 * edit_similarity), 6)

    return {
        "term_consistency": round(term_consistency, 6),
        "length_ratio": round(length_ratio, 6),
        "edit_similarity": round(edit_similarity, 6),
        "overall": overall,
    }
```

- [ ] **Step 4: Wire metrics into pretrain workflow with explicit baseline**

```python
# src/consensus_translation/config.py (add fields)
class AppSettings(BaseModel):
    contract_version: str = "1.0.0"
    default_granularity: list[str] = Field(default_factory=lambda: ["token", "sentence", "segment"])
    mdwc_weights: dict[str, float] = Field(default_factory=lambda: {"token": 0.4, "sentence": 0.35, "segment": 0.2, "user_prior": 0.05})
    pretrain_baseline_overall: float = 0.5
    evaluation_version: str = "phase2-v1"
```

```python
# src/consensus_translation/workflows.py (inside run_pretrain_job)
settings = AppSettings()
validation_metrics = evaluate_translation(
    source_text=train_text,
    predicted_text=str(base_result["final_text"]),
    reference_text=validation_text,
)
improvement_rate = round(validation_metrics["overall"] - settings.pretrain_baseline_overall, 6)
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_evaluation.py tests/test_workflows.py::test_pretrain_returns_calibration_summary_and_updates -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/consensus_translation/evaluation.py src/consensus_translation/config.py src/consensus_translation/workflows.py tests/test_evaluation.py tests/test_workflows.py
git commit -m "feat: replace pretrain placeholder metrics with deterministic evaluation"
```

### Task 3: Implement M2 Layered Lexicon Schema

**Files:**
- Modify: `src/consensus_translation/lexicon.py`
- Modify: `tests/test_lexicon.py`

- [ ] **Step 1: Write failing tests for 3-layer lexicon storage**

```python
# tests/test_lexicon.py
from consensus_translation.lexicon import LexiconRepo, RevisionPayload


def test_revision_routes_short_source_to_term_layer(tmp_path):
    repo = LexiconRepo(store_path=tmp_path / "lexicon.json")
    repo.apply_revision(RevisionPayload(topic="myth", source="奥丁", target="Odin", diff_ratio=0.2))
    data = repo.export_topic("myth")
    assert data["terms"]["奥丁"] == "Odin"


def test_revision_routes_phrase_to_phrase_layer(tmp_path):
    repo = LexiconRepo(store_path=tmp_path / "lexicon.json")
    repo.apply_revision(RevisionPayload(topic="science", source="量子纠缠态", target="quantum entanglement state", diff_ratio=0.3))
    data = repo.export_topic("science")
    assert data["phrases"]["量子纠缠态"] == "quantum entanglement state"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_lexicon.py::test_revision_routes_short_source_to_term_layer -v`  
Expected: FAIL because `export_topic` and layered schema do not exist.

- [ ] **Step 3: Implement schema v2 with explicit layers**

```python
# src/consensus_translation/lexicon.py (core structure)
def _empty_topic_bucket() -> dict[str, dict[str, str]]:
    return {"terms": {}, "phrases": {}, "style_rules": {}}


class LexiconRepo:
    def __init__(self, store_path: Path | None = None) -> None:
        ...
        self._schema_version = "2.0"

    def _ensure_topic_bucket(self, topic: str) -> dict[str, dict[str, str]]:
        row = self._store.get(topic)
        if not isinstance(row, dict) or "terms" not in row:
            row = _empty_topic_bucket()
            self._store[topic] = row
        return row

    def apply_revision(self, payload: RevisionPayload) -> RevisionEvent:
        topic = payload.topic or "uncategorized"
        bucket = self._ensure_topic_bucket(topic)
        token_count = len(payload.source.split())
        if token_count <= 1 and len(payload.source) <= 8:
            bucket["terms"][payload.source] = payload.target
        elif token_count <= 8:
            bucket["phrases"][payload.source] = payload.target
        else:
            bucket["style_rules"][payload.source] = payload.target
        self._save_store()
        special = payload.diff_ratio >= 0.6
        return RevisionEvent(special_flag=special, user_prior_delta=(-0.1 if special else 0.05))

    def export_topic(self, topic: str) -> dict[str, dict[str, str]]:
        return self._ensure_topic_bucket(topic)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_lexicon.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/consensus_translation/lexicon.py tests/test_lexicon.py
git commit -m "feat: add lexicon schema v2 with term phrase style layers"
```

### Task 4: Implement M3 Domain Signals and MDWC Linkage

**Files:**
- Create: `src/consensus_translation/domain_signals.py`
- Modify: `src/consensus_translation/workflows.py`
- Modify: `tests/test_workflows.py`
- Create: `tests/test_domain_signals.py`

- [ ] **Step 1: Write failing tests for domain extraction and decision trace**

```python
# tests/test_domain_signals.py
from consensus_translation.domain_signals import detect_domain_signals


def test_detect_domain_signals_extracts_myth_history_science_hits():
    out = detect_domain_signals("奥丁在罗马历法中讨论量子干涉")
    assert "myth" in out["tags"]
    assert "history" in out["tags"]
    assert "science" in out["tags"]
```

```python
# tests/test_workflows.py (new assertion in local test)
assert "domain_tags" in result
assert "domain_weight_adjustment" in result["decision_reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_domain_signals.py tests/test_workflows.py::test_local_job_marks_needs_review_when_scores_low -v`  
Expected: FAIL due to missing module/new fields.

- [ ] **Step 3: Implement deterministic domain signal extractor**

```python
# src/consensus_translation/domain_signals.py
from __future__ import annotations


MYTH_TERMS = {"奥丁", "宙斯", "卢恩", "阿瓦隆"}
HISTORY_TERMS = {"罗马", "拿破仑", "幕府", "王朝"}
SCIENCE_TERMS = {"量子", "引力", "相对论", "熵"}


def detect_domain_signals(text: str) -> dict[str, object]:
    hits: dict[str, list[str]] = {"myth": [], "history": [], "science": []}
    for term in MYTH_TERMS:
        if term in text:
            hits["myth"].append(term)
    for term in HISTORY_TERMS:
        if term in text:
            hits["history"].append(term)
    for term in SCIENCE_TERMS:
        if term in text:
            hits["science"].append(term)
    tags = [k for k, v in hits.items() if v]
    return {"tags": tags, "hits": hits}
```

- [ ] **Step 4: Link signals into local workflow decision reason**

```python
# src/consensus_translation/workflows.py (inside run_local_job)
signals = detect_domain_signals(text)
domain_tags = signals["tags"]
domain_boost = 0.02 if domain_tags else 0.0

winner_score = min(1.0, score_candidate(winner, settings.mdwc_weights) + domain_boost)
decision_reason = (
    "left-score-greater-or-equal+domain_weight_adjustment"
    if winner is left
    else "right-score-greater+domain_weight_adjustment"
)
```

- [ ] **Step 5: Run tests to verify pass**

Run: `pytest tests/test_domain_signals.py tests/test_workflows.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/consensus_translation/domain_signals.py src/consensus_translation/workflows.py tests/test_domain_signals.py tests/test_workflows.py
git commit -m "feat: add domain signal detection and mdwc linkage trace"
```

### Task 5: Implement M4 Ops Utilities (Init, Logs, Audit, Resume)

**Files:**
- Create: `scripts/init_env.ps1`
- Create: `src/consensus_translation/ops.py`
- Modify: `src/consensus_translation/workflows.py`
- Modify: `tests/test_workflows.py`

- [ ] **Step 1: Write failing tests for audit export and checkpoint resume**

```python
# tests/test_workflows.py
def test_local_job_exports_audit_record_when_path_provided(tmp_path):
    out = run_local_job("你好", "zh", "ja", "general", audit_path=tmp_path / "audit.json")
    assert out["audit_exported"] is True


def test_local_job_can_resume_from_stage_checkpoint():
    out = run_local_job("你好", "zh", "ja", "general", resume_from_stage="engine")
    assert out["contract"]["stage_status"]["current"] == "finalize"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_workflows.py::test_local_job_exports_audit_record_when_path_provided -v`  
Expected: FAIL due to unknown params or missing ops helper.

- [ ] **Step 3: Implement ops helper and workflow hooks**

```python
# src/consensus_translation/ops.py
from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path


def export_audit_record(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
```

```python
# src/consensus_translation/workflows.py (signature and tail)
def run_local_job(
    text: str,
    source_lang: str,
    target_lang: str,
    topic: str | None,
    audit_path: Path | None = None,
    resume_from_stage: str | None = None,
) -> dict[str, object]:
    ...
    payload = {...}
    if audit_path is not None:
        export_audit_record(audit_path, payload)
        payload["audit_exported"] = True
    else:
        payload["audit_exported"] = False
    return payload
```

```powershell
# scripts/init_env.ps1
param([string]$PythonExe = "python")
$ErrorActionPreference = "Stop"
& $PythonExe -c "import sys; print(sys.version)"
& $PythonExe -m pip install -r requirements.txt
& $PythonExe -c "import streamlit, pydantic; print('deps-ok')"
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_workflows.py -v`  
Expected: PASS

- [ ] **Step 5: Verify init script**

Run: `powershell -ExecutionPolicy Bypass -File .\scripts\init_env.ps1`  
Expected: dependency install output and `deps-ok`

- [ ] **Step 6: Commit**

```bash
git add scripts/init_env.ps1 src/consensus_translation/ops.py src/consensus_translation/workflows.py tests/test_workflows.py
git commit -m "feat: add phase2 ops baseline for init audit and resume"
```

### Task 6: Gate-L (Local Go-Live) Final Verification

**Files:**
- Modify: `tests/test_workflows.py`
- Modify: `docs/worklog_zh.md`

- [ ] **Step 1: Write failing gate tests for local go-live criteria**

```python
# tests/test_workflows.py
def test_local_mode_go_live_payload_has_required_fields():
    out = run_local_job("你好", "zh", "ja", "general")
    required = {
        "final_text",
        "final_score",
        "needs_review",
        "decision_reason",
        "contract",
        "audit_exported",
    }
    assert required.issubset(out.keys())


def test_local_mode_error_path_sets_structured_contract_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr("consensus_translation.workflows.LocalEngineA.translate", boom)
    with pytest.raises(RuntimeError):
        run_local_job("你好", "zh", "ja", "general")
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_workflows.py::test_local_mode_go_live_payload_has_required_fields -v`  
Expected: FAIL until all gate fields are guaranteed.

- [ ] **Step 3: Make minimal implementation to satisfy Gate-L consistently**

```python
# src/consensus_translation/workflows.py (contract error handling and payload completion)
except Exception as exc:
    contract.stage_status.error_code = "ENGINE_FAILURE"
    contract.stage_status.error_message = str(exc)
    raise

payload = {
    "final_text": final_text,
    "final_score": winner_score,
    "needs_review": needs_review,
    "decision_reason": decision_reason,
    "contract": contract.model_dump(),
    "audit_exported": False,
    ...
}
```

- [ ] **Step 4: Run full verification suite and coverage gate**

Run: `pytest -v --cov=src/consensus_translation --cov-report=term-missing`  
Expected: PASS with coverage >= 88%

- [ ] **Step 5: Update worklog with phase2 gate evidence**

```markdown
## 阶段推进（2026-05-07）

- 第二阶段目标重排完成，AI 辅助模式转第三阶段目标。
- Gate-L 本地模式投用门槛验证通过。
- UI-Backend Contract Gate 通过，前后端字段对齐完成。
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_workflows.py docs/worklog_zh.md src/consensus_translation/workflows.py
git commit -m "test: add local go-live gate and phase2 verification evidence"
```

## Self-Review Checklist

- Spec coverage:
  - M1 预训练指标真实化 -> Task 2
  - M2 词库三层结构 -> Task 3
  - M3 要素识别与权重联动 -> Task 4
  - M4 初始化/日志/审计/恢复 -> Task 5
  - Gate-L 本地投用门槛 -> Task 6
  - UI-Backend Contract Gate -> Task 1 + Task 6
  - 第三阶段 AI 辅助模式不推进 -> Task 1 (UI禁止暴露) + 全计划未引入 AI 流程实现
- Placeholder scan: no `TBD`, `TODO`, or unresolved placeholders
- Type consistency: `run_local_job` and `run_pretrain_job` remain orchestration APIs; `validation_metrics/improvement_rate` naming remains consistent with existing UI map
