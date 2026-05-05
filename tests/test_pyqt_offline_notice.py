import src.ui.pyqt_app.main_window as main_window


def test_network_available_returns_false_on_exception(monkeypatch) -> None:
    def raise_error(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(main_window.socket, "create_connection", raise_error)

    assert main_window.network_available(timeout=0.01) is False


def test_offline_notice_text_contains_expected_message() -> None:
    text = main_window.offline_notice_text()

    assert "未联网" in text
    assert "部分功能受限" in text


def test_module_supports_direct_execution_entrypoint() -> None:
    assert hasattr(main_window, "run")
