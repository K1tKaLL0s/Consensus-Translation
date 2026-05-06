from __future__ import annotations

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

from consensus_translation.contracts import TranslationJobContract


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

    st.set_page_config(page_title="Cn-Jp Translation UI Contract", layout="wide")
    st.title("Cn-Jp Translation UI Contract")

    selected_page = st.sidebar.selectbox("Select page", options=list(PAGE_FIELD_MAP.keys()))

    st.subheader(f"Page: {selected_page}")
    st.json(PAGE_FIELD_MAP[selected_page])

    contract_fields = list(TranslationJobContract.model_fields.keys())
    st.subheader("contract_fields")
    st.json(contract_fields)


if __name__ == "__main__":
    main()
