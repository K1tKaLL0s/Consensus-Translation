from pathlib import Path

import requests

from src.services.translation_service import (
    validate_source_declaration,
    validate_translation_input,
)


SUPPORTED_UPLOAD_TYPES = ["txt", "md", "docx"]
SUPPORTED_PROVIDERS = ["gpt", "qwen", "kimi", "deepseek", "gemini", "watsonx"]


def validate_submission(mode: str, source: str, text: str) -> tuple[bool, str]:
    source_ok, source_message = validate_source_declaration(source)
    if not source_ok:
        return False, source_message

    if mode == "翻译":
        text_ok, text_message = validate_translation_input(text)
        if not text_ok:
            return False, text_message

    return True, "提交成功"


def validate_upload_name(filename: str) -> tuple[bool, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ".docx"}:
        return False, "only txt/md/docx are supported"
    return True, "ok"


def _handle_response(response: requests.Response) -> tuple[bool, dict[str, object]]:
    try:
        payload = response.json()
    except ValueError:
        return False, {"detail": f"http {response.status_code}"}
    if response.status_code >= 400:
        return False, payload
    return True, payload


def render_network_status_panel(api_base_url: str) -> None:
    import streamlit as st

    st.subheader("网络状态")

    try:
        response = requests.get(f"{api_base_url}/system/network", timeout=10)
    except requests.RequestException as exc:
        st.error(str(exc))
        return

    ok, payload = _handle_response(response)
    if not ok:
        st.error(str(payload.get("detail", "读取网络状态失败")))
        return

    st.write(f"online: {payload.get('online')}")
    st.write(f"checked_at: {payload.get('checked_at')}")
    st.write(f"probe_target: {payload.get('probe_target')}")
    st.write(f"latency_ms: {payload.get('latency_ms')}")
    st.write(f"message: {payload.get('message')}")

    if st.button("刷新网络状态"):
        st.rerun()


def render_llm_config_panel(api_base_url: str) -> None:
    import streamlit as st

    st.subheader("LLM 全局配置")
    provider = st.selectbox("provider", SUPPORTED_PROVIDERS)
    model = st.text_input("model")
    api_key = st.text_input("api_key", type="password")

    col1, col2, col3 = st.columns(3)
    if col1.button("保存配置"):
        response = requests.post(
            f"{api_base_url}/config/llm",
            json={"provider": provider, "model": model, "api_key": api_key},
            timeout=10,
        )
        ok, payload = _handle_response(response)
        if ok:
            st.success("配置已保存")
        else:
            st.error(str(payload.get("detail", "保存失败")))

    if col2.button("删除配置"):
        response = requests.delete(f"{api_base_url}/config/llm", timeout=10)
        ok, payload = _handle_response(response)
        if ok:
            st.success("配置已删除")
        else:
            st.error(str(payload.get("detail", "删除失败")))

    if col3.button("刷新状态"):
        st.rerun()


def render_config_monitor_window(api_base_url: str) -> None:
    import streamlit as st

    st.subheader("配置监控窗口")
    response = requests.get(f"{api_base_url}/config/llm", timeout=10)
    ok, payload = _handle_response(response)
    if not ok:
        st.error(str(payload.get("detail", "读取配置状态失败")))
        return

    st.write(f"provider: {payload.get('provider')}")
    st.write(f"model: {payload.get('model')}")
    st.write(f"api_key_configured: {payload.get('api_key_configured')}")
    st.write(f"updated_at: {payload.get('updated_at')}")


def render_file_task_panel(api_base_url: str) -> None:
    import streamlit as st

    st.subheader("文件任务")
    usage = st.radio("用途", ["translate", "glossary"], horizontal=True)
    source = st.text_input("来源/主题（必填）", key="file_source")
    upload = st.file_uploader("上传文件（txt/md/docx）", type=SUPPORTED_UPLOAD_TYPES)

    if st.button("提交文件任务"):
        if upload is None:
            st.error("请先上传文件")
            return

        valid_file, file_message = validate_upload_name(upload.name)
        if not valid_file:
            st.error(file_message)
            return

        source_ok, source_message = validate_source_declaration(source)
        if not source_ok:
            st.error(source_message)
            return

        files = {
            "file": (
                upload.name,
                upload.getvalue(),
                "application/octet-stream",
            )
        }
        data = {"usage": usage, "source_declaration": source}
        response = requests.post(f"{api_base_url}/tasks/file", data=data, files=files, timeout=60)
        ok, payload = _handle_response(response)
        if not ok:
            st.error(str(payload.get("detail", "提交失败")))
            return

        st.success(f"任务完成: {payload.get('task_id')}")
        if usage == "translate":
            task_id = payload.get("task_id")
            st.markdown(f"下载结果: {api_base_url}/downloads/{task_id}")


def render() -> None:
    import streamlit as st

    st.title("CN-JP UI")

    api_base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")

    render_network_status_panel(api_base_url)
    st.divider()
    render_llm_config_panel(api_base_url)
    render_config_monitor_window(api_base_url)
    st.divider()
    render_file_task_panel(api_base_url)
    st.divider()

    mode = st.selectbox("mode", ["翻译", "训练"])
    source = st.text_input("来源/主题（可自由输入）")
    text = st.text_area("text")

    if st.button("提交"):
        ok, message = validate_submission(mode=mode, source=source, text=text)
        if ok:
            st.success(message)
        else:
            st.error(message)


if __name__ == "__main__":
    render()
