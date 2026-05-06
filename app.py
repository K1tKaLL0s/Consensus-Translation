from __future__ import annotations

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

from consensus_translation.config import AppSettings
from consensus_translation.contracts import TranslationJobContract


PAGE_FIELD_MAP: dict[str, list[str]] = {
    "config": [
        "contract_version",
        "default_granularity",
        "mdwc_weights",
    ],
    "monitor": list(TranslationJobContract.model_fields.keys()),
    "compare": [
        "left_text",
        "right_text",
        "left_score",
        "right_score",
        "winner",
        "final_score",
        "needs_review",
    ],
    "mdwc": [
        "token_score",
        "sentence_score",
        "segment_score",
        "user_prior",
        "locked_term_ok",
        "weighted_score",
    ],
    "revision": [
        "topic",
        "source",
        "target",
        "diff_ratio",
        "special_flag",
        "user_prior_delta",
    ],
    "pretrain_report": [
        "mode",
        "base_result",
        "validation_text",
        "calibration_summary",
        "lexicon_updates",
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
