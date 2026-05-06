from __future__ import annotations

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
            _, value = _resolve_dot_path_with_found(data, f"contract.{key}")
            if value is _MISSING:
                value = None
        values[key] = value
    return values


def main() -> None:
    if st is None:  # pragma: no cover
        raise RuntimeError("streamlit is required to run the UI")

    st.set_page_config(page_title="Consensus Translation V1", layout="wide")
    st.title("Consensus Translation V1")

    if "latest_payload" not in st.session_state:
        st.session_state["latest_payload"] = {}

    st.sidebar.header("Run Jobs")
    source_lang = st.sidebar.text_input("Source Lang", value="zh")
    target_lang = st.sidebar.text_input("Target Lang", value="ja")
    topic = st.sidebar.text_input("Topic", value="general")

    local_text = st.sidebar.text_area("Local Text", value="你好")
    if st.sidebar.button("Run Local Job"):
        st.session_state["latest_payload"] = run_local_job(
            text=local_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )

    train_text = st.sidebar.text_area("Pretrain Text", value="车站")
    validation_text = st.sidebar.text_area("Validation Text", value="列车")
    if st.sidebar.button("Run Pretrain Job"):
        st.session_state["latest_payload"] = run_pretrain_job(
            train_text=train_text,
            validation_text=validation_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )

    page = st.sidebar.selectbox("Page", list(PAGE_FIELD_MAP.keys()))
    page_data = extract_page_data(page, st.session_state.get("latest_payload"))

    st.subheader(page)
    st.json(page_data)


if __name__ == "__main__":
    main()
