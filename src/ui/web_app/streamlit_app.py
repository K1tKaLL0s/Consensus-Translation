from src.services.translation_service import (
    validate_source_declaration,
    validate_translation_input,
)


def validate_submission(mode: str, source: str, text: str) -> tuple[bool, str]:
    source_ok, source_message = validate_source_declaration(source)
    if not source_ok:
        return False, source_message

    if mode == "翻译":
        text_ok, text_message = validate_translation_input(text)
        if not text_ok:
            return False, text_message

    return True, "提交成功"


def render() -> None:
    import streamlit as st

    st.title("CN-JP UI")

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
