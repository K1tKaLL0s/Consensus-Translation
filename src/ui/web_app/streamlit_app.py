def validate_submission(mode: str, source: str, text: str) -> tuple[bool, str]:
    if not source.strip():
        return False, "来源/主题不能为空"

    if mode == "翻译" and len(text) > 1000:
        return False, "翻译模式文本长度不能超过1000"

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
