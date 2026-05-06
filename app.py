from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys
from typing import Literal, TypedDict


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

EXT_TXT = ".txt"
EXT_MD = ".md"
EXT_DOCX = ".docx"

SUPPORTED_TEXT_EXTENSIONS = {EXT_TXT, EXT_MD}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | {EXT_DOCX}

MIME_TEXT_PLAIN = "text/plain"
MIME_TEXT_MARKDOWN = "text/markdown"
MIME_TEXT_X_MARKDOWN = "text/x-markdown"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

ALLOWED_MIME_BY_EXT: dict[str, set[str]] = {
    EXT_TXT: {MIME_TEXT_PLAIN},
    EXT_MD: {MIME_TEXT_MARKDOWN, MIME_TEXT_X_MARKDOWN, MIME_TEXT_PLAIN},
    EXT_DOCX: {MIME_DOCX},
}

REASON_NO_FILE = "no_file"
REASON_INVALID_FILE_OBJ = "invalid_file_obj"
REASON_INVALID_FILE_BYTES = "invalid_file_bytes"
REASON_UNSUPPORTED_TYPE = "unsupported_type"
REASON_DECODE_ERROR = "decode_error"
REASON_DOCX_PARSE_ERROR = "docx_parse_error"
REASON_DOCX_DEP_MISSING = "docx_dependency_missing"


UploadParseReason = Literal[
    "no_file",
    "invalid_file_obj",
    "invalid_file_bytes",
    "unsupported_type",
    "decode_error",
    "docx_parse_error",
    "docx_dependency_missing",
]


class UploadParseMetadata(TypedDict):
    ok: bool
    file_name: str | None
    file_type: str | None
    file_ext: str | None
    reason: UploadParseReason | None


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


def extract_uploaded_text(uploaded_file: object | None) -> tuple[str, UploadParseMetadata]:
    metadata: UploadParseMetadata = {
        "ok": False,
        "file_name": None,
        "file_type": None,
        "file_ext": None,
        "reason": REASON_NO_FILE,
    }
    if uploaded_file is None:
        return "", metadata

    file_name = str(getattr(uploaded_file, "name", "") or "")
    file_type = str(getattr(uploaded_file, "type", "") or "")
    file_ext = Path(file_name).suffix.lower()
    metadata.update({"file_name": file_name, "file_type": file_type, "file_ext": file_ext})

    getvalue = getattr(uploaded_file, "getvalue", None)
    if not callable(getvalue):
        metadata["reason"] = REASON_INVALID_FILE_OBJ
        return "", metadata

    raw = getvalue()
    if not isinstance(raw, (bytes, bytearray)):
        metadata["reason"] = REASON_INVALID_FILE_BYTES
        return "", metadata
    raw_bytes = bytes(raw)

    if file_ext not in SUPPORTED_EXTENSIONS:
        metadata["reason"] = REASON_UNSUPPORTED_TYPE
        return "", metadata

    allowed_mimes = ALLOWED_MIME_BY_EXT.get(file_ext, set())
    if file_type and file_type not in allowed_mimes:
        metadata["reason"] = REASON_UNSUPPORTED_TYPE
        return "", metadata

    if file_ext in SUPPORTED_TEXT_EXTENSIONS:
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            metadata["reason"] = REASON_DECODE_ERROR
            return "", metadata
        metadata.update({"ok": True, "reason": None})
        return text, metadata

    if file_ext == EXT_DOCX:
        try:
            from docx import Document
        except ModuleNotFoundError:
            metadata["reason"] = REASON_DOCX_DEP_MISSING
            return "", metadata

        try:
            doc = Document(BytesIO(raw_bytes))
        except Exception:
            metadata["reason"] = REASON_DOCX_PARSE_ERROR
            return "", metadata
        text = "\n".join(p.text for p in doc.paragraphs)
        metadata.update({"ok": True, "reason": None})
        return text, metadata

    metadata["reason"] = REASON_UNSUPPORTED_TYPE
    return "", metadata


def resolve_input_text(
    manual_text: str | None,
    uploaded_text: str | None,
    uploaded_meta: dict[str, object] | None,
) -> tuple[str, dict[str, object]]:
    meta = dict(uploaded_meta or {})
    upload_ok = bool(meta.get("ok"))
    upload_text = uploaded_text or ""
    if upload_ok and upload_text.strip():
        meta["source"] = "upload"
        return upload_text, meta

    meta["source"] = "manual"
    return manual_text or "", meta


def build_result_panel(payload: dict[str, object] | None) -> dict[str, object]:
    data = payload or {}
    mode = data.get("mode")
    local_payload = data
    if mode == "pretrain":
        base_result = data.get("base_result")
        if isinstance(base_result, dict):
            local_payload = base_result

    return {
        "mode": mode,
        "local_final_text": local_payload.get("final_text"),
        "local_final_score": local_payload.get("final_score"),
        "local_needs_review": local_payload.get("needs_review"),
        "local_decision_reason": local_payload.get("decision_reason"),
        "pretrain_calibration_summary": data.get("calibration_summary"),
        "pretrain_improvement_rate": data.get("improvement_rate"),
    }


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

    uploaded_file = st.sidebar.file_uploader(
        "上传文本文件（txt/md/docx）",
        type=["txt", "md", "docx"],
    )
    uploaded_text, upload_meta = extract_uploaded_text(uploaded_file)
    if uploaded_file is None:
        st.sidebar.info("未上传文件，使用手动输入内容。")
    elif upload_meta.get("ok"):
        if uploaded_text.strip():
            st.sidebar.success("文件加载成功，运行时优先使用上传文本。")
        else:
            st.sidebar.warning("文件已加载但内容为空，运行时将回退到手动输入。")
    else:
        reason = str(upload_meta.get("reason") or REASON_UNSUPPORTED_TYPE)
        st.sidebar.error(f"文件加载失败：{reason}")

    local_text = st.sidebar.text_area("本地文本", value="你好")
    effective_local_text, effective_local_meta = resolve_input_text(
        local_text,
        uploaded_text,
        upload_meta,
    )
    st.sidebar.caption(f"本地任务输入来源：{effective_local_meta.get('source', 'manual')}")
    if st.sidebar.button("运行本地任务"):
        st.session_state["latest_payload"] = run_local_job(
            text=effective_local_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )

    train_text = st.sidebar.text_area("预训练文本", value="车站")
    effective_train_text, effective_train_meta = resolve_input_text(
        train_text,
        uploaded_text,
        upload_meta,
    )
    st.sidebar.caption(f"预训练输入来源：{effective_train_meta.get('source', 'manual')}")
    validation_text = st.sidebar.text_area("验证文本", value="列车")
    if st.sidebar.button("运行预训练任务"):
        st.session_state["latest_payload"] = run_pretrain_job(
            train_text=effective_train_text,
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

    st.subheader("翻译结果")
    st.json(build_result_panel(st.session_state.get("latest_payload")))


if __name__ == "__main__":
    main()
