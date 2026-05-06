import pytest

import src.ui.web_app.streamlit_app as streamlit_app


def test_module_exposes_render_network_status_panel() -> None:
    assert hasattr(streamlit_app, "render_network_status_panel")


def test_render_network_status_panel_fetches_and_shows_fields(monkeypatch) -> None:
    calls: dict[str, object] = {"url": None, "timeout": None}

    class _Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "online": True,
                "checked_at": "2026-05-06T00:00:00+00:00",
                "probe_target": "1.1.1.1:53",
                "latency_ms": 11.2,
                "message": "网络连接正常",
            }

    def _fake_get(url: str, timeout: int):
        calls["url"] = url
        calls["timeout"] = timeout
        return _Response()

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.lines: list[str] = []

        def subheader(self, text: str) -> None:
            self.lines.append(f"subheader:{text}")

        def write(self, text: str) -> None:
            self.lines.append(text)

        def button(self, _label: str) -> bool:
            return False

        def rerun(self) -> None:
            self.lines.append("rerun")

        def error(self, text: str) -> None:
            self.lines.append(f"error:{text}")

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(streamlit_app.requests, "get", _fake_get)
    monkeypatch.setitem(__import__("sys").modules, "streamlit", fake_st)

    streamlit_app.render_network_status_panel("http://127.0.0.1:8000")

    assert calls["url"] == "http://127.0.0.1:8000/system/network"
    assert calls["timeout"] == 10
    assert "subheader:网络状态" in fake_st.lines
    assert "online: True" in fake_st.lines
    assert "checked_at: 2026-05-06T00:00:00+00:00" in fake_st.lines
    assert "probe_target: 1.1.1.1:53" in fake_st.lines
    assert "latency_ms: 11.2" in fake_st.lines
    assert "message: 网络连接正常" in fake_st.lines


def test_render_network_status_panel_refresh_button_reruns(monkeypatch) -> None:
    class _Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "online": False,
                "checked_at": "2026-05-06T00:00:00+00:00",
                "probe_target": "1.1.1.1:53",
                "latency_ms": None,
                "message": "当前未联网",
            }

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.rerun_called = False

        def subheader(self, _text: str) -> None:
            pass

        def write(self, _text: str) -> None:
            pass

        def button(self, _label: str) -> bool:
            return True

        def rerun(self) -> None:
            self.rerun_called = True

        def error(self, _text: str) -> None:
            pass

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(streamlit_app.requests, "get", lambda *_args, **_kwargs: _Response())
    monkeypatch.setitem(__import__("sys").modules, "streamlit", fake_st)

    streamlit_app.render_network_status_panel("http://127.0.0.1:8000")

    assert fake_st.rerun_called is True


@pytest.mark.parametrize("exc", [streamlit_app.requests.Timeout, streamlit_app.requests.RequestException])
def test_render_network_status_panel_handles_request_exception(monkeypatch, exc) -> None:
    class _FakeStreamlit:
        def __init__(self) -> None:
            self.errors: list[str] = []

        def subheader(self, _text: str) -> None:
            pass

        def write(self, _text: str) -> None:
            pass

        def button(self, _label: str) -> bool:
            return False

        def rerun(self) -> None:
            pass

        def error(self, text: str) -> None:
            self.errors.append(text)

    def _raise_request_exception(*_args, **_kwargs):
        raise exc("network request failed")

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(streamlit_app.requests, "get", _raise_request_exception)
    monkeypatch.setitem(__import__("sys").modules, "streamlit", fake_st)

    streamlit_app.render_network_status_panel("http://127.0.0.1:8000")

    assert len(fake_st.errors) == 1
    assert "network request failed" in fake_st.errors[0]


def test_render_calls_network_panel_before_existing_sections(monkeypatch) -> None:
    call_order: list[str] = []

    class _FakeStreamlit:
        def title(self, _text: str) -> None:
            pass

        def text_input(self, _label: str, value: str = "", **_kwargs) -> str:
            return value

        def divider(self) -> None:
            pass

        def selectbox(self, _label: str, options: list[str]) -> str:
            return options[0]

        def text_area(self, _label: str) -> str:
            return ""

        def button(self, _label: str) -> bool:
            return False

        def success(self, _text: str) -> None:
            pass

        def error(self, _text: str) -> None:
            pass

    monkeypatch.setitem(__import__("sys").modules, "streamlit", _FakeStreamlit())
    monkeypatch.setattr(streamlit_app, "render_network_status_panel", lambda _url: call_order.append("network"))
    monkeypatch.setattr(streamlit_app, "render_llm_config_panel", lambda _url: call_order.append("llm"))
    monkeypatch.setattr(streamlit_app, "render_config_monitor_window", lambda _url: call_order.append("monitor"))
    monkeypatch.setattr(streamlit_app, "render_file_task_panel", lambda _url: call_order.append("file"))

    streamlit_app.render()

    assert call_order[:4] == ["network", "llm", "monitor", "file"]
