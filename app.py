from __future__ import annotations

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

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


def main() -> None:
    if st is None:  # pragma: no cover
        raise RuntimeError("streamlit is required to run the UI")

    st.set_page_config(page_title="Consensus Translation V1", layout="wide")
    st.title("Consensus Translation V1")

    page = st.sidebar.selectbox("Page", list(PAGE_FIELD_MAP.keys()))

    st.subheader(page)
    st.json({"contract_fields": PAGE_FIELD_MAP[page]})


if __name__ == "__main__":
    main()
