def validate_submission(mode: str, source: str, text: str) -> tuple[bool, str]:
    if not source.strip():
        return False, "source is required"

    if mode == "翻译" and len(text) > 1000:
        return False, "text length must be <= 1000"

    return True, "submission accepted"


def render() -> None:
    import streamlit as st

    st.title("CN-JP UI")

    mode = st.selectbox("mode", ["翻译", "训练"])
    source = st.text_input("source")
    text = st.text_area("text")

    if st.button("提交"):
        ok, message = validate_submission(mode=mode, source=source, text=text)
        if ok:
            st.success(message)
        else:
            st.error(message)


if __name__ == "__main__":
    render()
