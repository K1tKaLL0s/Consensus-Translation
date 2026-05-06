from __future__ import annotations
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

from consensus_translation.workflows import run_local_job, run_pretrain_job

PAGE_FIELD_MAP: dict[str, list[str]] = {
    "config": [
        "job_id",
        "mode",
        "source_lang",
        "target_lang",
        "topic",
        "domain_tags",
        "granularity",
    ],
    "monitor": [
        "stage_status.current",
        "stage_status.progress",
        "stage_status.retry_count",
        "stage_status.error_code",
        "stage_status.error_message",
    ],
    "compare": [
        "cand_a",
        "cand_b",
        "token_diff",
        "sentence_diff",
        "segment_diff",
        "overlap_score",
        "confidence_a",
        "confidence_b",
        "term_consistency",
    ],
    "mdwc": [
        "weights",
        "token_score",
        "sentence_score",
        "segment_score",
        "user_prior",
        "final_score",
        "decision_reason",
    ],
    "revision": [
        "user_revision",
        "diff",
        "special_flag",
        "lexicon_updates",
        "theme_bucket",
        "update_status",
    ],
    "pretrain_report": [
        "validation_metrics",
        "improvement_rate",
        "conflict_terms",
        "uncategorized_terms",
        "calibration_summary",
    ],
}

PAGE_LABEL_MAP: dict[str, str] = {
    "config": "配置",
    "monitor": "监控",
    "compare": "对比",
    "mdwc": "MDWC评分",
    "revision": "修订",
    "pretrain_report": "预训练报告",
}


_MISSING = object()


def _resolve_dot_path_with_found(payload: dict[str, object], path: str) -> tuple[bool, object]:
    current: object = payload
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return False, _MISSING
        current = current[key]
    return True, current


def resolve_dot_path(payload: dict[str, object], path: str) -> object:
    found, value = _resolve_dot_path_with_found(payload, path)
    if not found:
        return None
    return value


def extract_page_data(page: str, payload: dict[str, object] | None) -> dict[str, object]:
    values: dict[str, object] = {}
    data = payload or {}
    for key in PAGE_FIELD_MAP[page]:
        found, value = _resolve_dot_path_with_found(data, key)
        if not found:
            fallback_found, fallback_value = _resolve_dot_path_with_found(data, f"contract.{key}")
            if fallback_found:
                value = fallback_value
            else:
                value = None
        values[key] = value
    return values


def get_page_select_keys() -> list[str]:
    return list(PAGE_FIELD_MAP.keys())


def main() -> None:
    if st is None:  # pragma: no cover
        raise RuntimeError("streamlit is required to run the UI")

    st.set_page_config(page_title="共识翻译 V1", layout="wide")
    st.title("共识翻译 V1")

    if "latest_payload" not in st.session_state:
        st.session_state["latest_payload"] = {}

    st.sidebar.header("任务运行")
    source_lang = st.sidebar.text_input("源语言", value="zh")
    target_lang = st.sidebar.text_input("目标语言", value="ja")
    topic = st.sidebar.text_input("主题", value="general")

    local_text = st.sidebar.text_area("本地文本", value="你好")
    if st.sidebar.button("运行本地任务"):
        st.session_state["latest_payload"] = run_local_job(
            text=local_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )

    train_text = st.sidebar.text_area("预训练文本", value="车站")
    validation_text = st.sidebar.text_area("验证文本", value="列车")
    if st.sidebar.button("运行预训练任务"):
        st.session_state["latest_payload"] = run_pretrain_job(
            train_text=train_text,
            validation_text=validation_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )

    page = st.sidebar.selectbox(
        "页面",
        get_page_select_keys(),
        format_func=lambda key: PAGE_LABEL_MAP.get(key, key),
    )
    page_data = extract_page_data(page, st.session_state.get("latest_payload"))

    st.subheader(PAGE_LABEL_MAP[page])
    st.json(page_data)


if __name__ == "__main__":
    main()
