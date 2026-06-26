from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys
from typing import Callable, Literal, TypedDict


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

from consensus_translation.workflows import apply_local_revision, run_local_job, run_pretrain_job

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

LANGUAGE_OPTIONS = ["zh", "en", "ja"]


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


class FinalOutputActionState(TypedDict):
    finalized: bool
    should_writeback: bool


class FinalOutputDisplayState(TypedDict):
    show_final_output: bool
    show_provisional: bool


def build_payload_context(payload: dict[str, object] | None) -> str | None:
    data = payload or {}
    mode = str(data.get("mode") or "")
    provisional = str(data.get("provisional_text") or "")
    if provisional.strip():
        return f"{mode}:{provisional}"
    return None


def clear_chat_revision_state(session_state: dict[str, object]) -> None:
    session_state["final_output_text"] = ""
    session_state["last_revision_text"] = ""
    session_state["revision_state"] = {}
    session_state["awaiting_revision"] = False
    session_state["final_output_context"] = None
    session_state["revision_error"] = None
    session_state["local_run_error"] = None


def decide_final_output_display(
    payload: dict[str, object] | None,
    final_output_text: str,
    final_output_context: str | None,
) -> FinalOutputDisplayState:
    payload_context = build_payload_context(payload)
    show_final_output = bool(
        final_output_text and payload_context and final_output_context == payload_context
    )
    show_provisional = bool(not show_final_output and payload_context)
    return {
        "show_final_output": show_final_output,
        "show_provisional": show_provisional,
    }


def run_apply_local_revision_safe(
    apply_revision_fn: Callable[..., dict[str, object]],
    source_text: str,
    provisional_text: str,
    revised_text: str,
    topic: str,
) -> tuple[dict[str, object], str | None]:
    try:
        result = apply_revision_fn(
            source_text=source_text,
            provisional_text=provisional_text,
            revised_text=revised_text,
            topic=topic,
        )
        return result, None
    except Exception as exc:
        return {}, str(exc)


def build_local_failure_payload() -> dict[str, object]:
    return {
        "mode": "local",
        "provisional_text": "翻译失败",
    }


def run_local_job_safe(
    run_local_job_fn: Callable[..., dict[str, object]],
    text: str,
    source_lang: str,
    target_lang: str,
    topic: str,
) -> tuple[dict[str, object], str | None]:
    try:
        payload = run_local_job_fn(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )
        return payload, None
    except Exception as exc:
        return build_local_failure_payload(), str(exc)


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


def resolve_topic_value(selected_topic: str, manual_topic: str) -> str:
    manual_value = (manual_topic or "").strip()
    if manual_value:
        return manual_value
    return selected_topic


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


def build_result_panel(
    payload: dict[str, object] | None,
    revision_error: str | None = None,
    local_run_error: str | None = None,
) -> dict[str, object]:
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
        "revision_writeback_error": revision_error,
        "local_run_error": local_run_error,
    }


def build_sidebar_detail_payload(
    page_key: str,
    page_data: dict[str, object],
    latest_payload: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "page_key": page_key,
        "page_label": PAGE_LABEL_MAP.get(page_key, page_key),
        "page_data": page_data,
        "state": latest_payload or {},
    }


def decide_final_output_action(
    action: str,
    revised_text: str,
    has_provisional: bool,
) -> FinalOutputActionState:
    if not has_provisional:
        return {"finalized": False, "should_writeback": False}
    if action == "confirm":
        return {"finalized": True, "should_writeback": False}
    if action == "revise" and revised_text.strip():
        return {"finalized": False, "should_writeback": True}
    return {"finalized": False, "should_writeback": False}


def main() -> None:
    if st is None:  # pragma: no cover
        raise RuntimeError("streamlit is required to run the UI")

    st.set_page_config(page_title="共识翻译 V1", layout="wide")
    st.title("共识翻译 V1")

    if "latest_payload" not in st.session_state:
        st.session_state["latest_payload"] = {}
    if "awaiting_revision" not in st.session_state:
        st.session_state["awaiting_revision"] = False

    st.sidebar.header("任务运行")
    source_lang = st.sidebar.selectbox("源语言", LANGUAGE_OPTIONS, index=0)
    target_lang = st.sidebar.selectbox("目标语言", LANGUAGE_OPTIONS, index=2)
    selected_topic = st.sidebar.selectbox(
        "主题（预设）",
        ["general", "travel", "greeting", "history", "science"],
        index=0,
    )
    manual_topic = st.sidebar.text_input("主题（手动覆盖）", value="")
    topic = resolve_topic_value(selected_topic, manual_topic)
    st.sidebar.caption(f"当前主题：{topic}")

    local_text = st.sidebar.text_area("本地文本", value="你好")
    local_file = st.sidebar.file_uploader(
        "上传本地文本（txt/md/docx）",
        type=["txt", "md", "docx"],
        key="local_file",
    )
    local_uploaded_text, local_upload_meta = extract_uploaded_text(local_file)
    effective_local_text, effective_local_meta = resolve_input_text(
        local_text,
        local_uploaded_text,
        local_upload_meta,
    )
    st.sidebar.caption(f"本地任务输入来源：{effective_local_meta.get('source', 'manual')}")
    if st.sidebar.button("运行本地任务"):
        st.session_state["last_source_text"] = effective_local_text
        st.session_state["last_topic"] = topic
        clear_chat_revision_state(st.session_state)
        payload, local_run_error = run_local_job_safe(
            run_local_job_fn=run_local_job,
            text=effective_local_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )
        st.session_state["latest_payload"] = payload
        st.session_state["local_run_error"] = local_run_error

    train_text = st.sidebar.text_area("预训练文本", value="车站")
    train_file = st.sidebar.file_uploader(
        "上传预训练文本（txt/md/docx）",
        type=["txt", "md", "docx"],
        key="train_file",
    )
    train_uploaded_text, train_upload_meta = extract_uploaded_text(train_file)
    effective_train_text, effective_train_meta = resolve_input_text(
        train_text,
        train_uploaded_text,
        train_upload_meta,
    )
    st.sidebar.caption(f"预训练输入来源：{effective_train_meta.get('source', 'manual')}")
    validation_text = st.sidebar.text_area("验证文本", value="列车")
    validation_file = st.sidebar.file_uploader(
        "上传验证文本（txt/md/docx）",
        type=["txt", "md", "docx"],
        key="validation_file",
    )
    validation_uploaded_text, validation_upload_meta = extract_uploaded_text(validation_file)
    effective_validation_text, effective_validation_meta = resolve_input_text(
        validation_text,
        validation_uploaded_text,
        validation_upload_meta,
    )
    st.sidebar.caption(f"验证输入来源：{effective_validation_meta.get('source', 'manual')}")
    if st.sidebar.button("运行预训练任务"):
        clear_chat_revision_state(st.session_state)
        st.session_state["latest_payload"] = run_pretrain_job(
            train_text=effective_train_text,
            validation_text=effective_validation_text,
            source_lang=source_lang,
            target_lang=target_lang,
            topic=topic,
        )

    page = st.sidebar.selectbox(
        "页面",
        get_page_select_keys(),
        format_func=lambda key: PAGE_LABEL_MAP.get(key, key),
    )
    latest_payload = st.session_state.get("latest_payload")
    page_data = extract_page_data(page, latest_payload)
    detail_payload = build_sidebar_detail_payload(page, page_data, latest_payload)
    with st.sidebar.expander("页面详情与状态", expanded=False):
        st.json(detail_payload)
    with st.sidebar.expander("结果详情（技术）", expanded=False):
        st.json(
            build_result_panel(
                latest_payload,
                revision_error=st.session_state.get("revision_error"),
                local_run_error=st.session_state.get("local_run_error"),
            )
        )

    st.subheader("翻译结果")
    provisional_text = str((latest_payload or {}).get("provisional_text") or "")
    final_output = str(st.session_state.get("final_output_text") or "")
    final_output_context = st.session_state.get("final_output_context")
    payload_context = build_payload_context(latest_payload)
    display_state = decide_final_output_display(latest_payload, final_output, final_output_context)
    has_provisional = bool(provisional_text.strip())
    local_run_failed = bool(st.session_state.get("local_run_error"))

    if display_state["show_final_output"]:
        revision_text = str(st.session_state.get("last_revision_text") or "")
        if revision_text:
            with st.chat_message("user"):
                st.write(revision_text)
        with st.chat_message("assistant"):
            st.write(final_output)
    elif display_state["show_provisional"] and has_provisional:
        with st.chat_message("assistant"):
            st.write(provisional_text)

        if local_run_failed and provisional_text == "翻译失败":
            return

        confirm_col, revise_col = st.columns(2)
        confirm_clicked = confirm_col.button("确认", key="confirm_result")
        revise_clicked = revise_col.button("修正", key="revise_result")

        if confirm_clicked:
            action_state = decide_final_output_action("confirm", "", has_provisional)
            if bool(action_state.get("finalized")):
                st.session_state["final_output_text"] = provisional_text
                st.session_state["final_output_context"] = payload_context
                st.session_state["awaiting_revision"] = False
                st.session_state["revision_error"] = None
                st.rerun()

        if revise_clicked:
            st.session_state["awaiting_revision"] = True

        if st.session_state.get("awaiting_revision", False):
            user_revision = st.chat_input("请输入修正内容", key="revision_input")
            if user_revision is not None:
                action_state = decide_final_output_action("revise", user_revision, has_provisional)
                if bool(action_state.get("should_writeback")):
                    revision_result, revision_error = run_apply_local_revision_safe(
                        apply_revision_fn=apply_local_revision,
                        source_text=str(st.session_state.get("last_source_text") or ""),
                        provisional_text=provisional_text,
                        revised_text=user_revision,
                        topic=str(st.session_state.get("last_topic") or topic),
                    )
                    if revision_error is None:
                        st.session_state["revision_state"] = revision_result
                        st.session_state["last_revision_text"] = user_revision
                        st.session_state["final_output_text"] = user_revision
                        st.session_state["final_output_context"] = payload_context
                        st.session_state["awaiting_revision"] = False
                        st.session_state["revision_error"] = None
                        st.rerun()
                    else:
                        st.session_state["revision_error"] = revision_error


if __name__ == "__main__":
    main()
