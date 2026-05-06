import os

from src.ui.pyqt_app.main_window import MainWindow


def qt_app():
    from PyQt6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _NetworkApiStub:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def get_network_status(self) -> dict[str, object]:
        return self.payload


def test_main_window_has_network_status_controls(monkeypatch) -> None:
    app = qt_app()
    monkeypatch.setattr("src.ui.pyqt_app.main_window.network_available", lambda: True)
    monkeypatch.setattr(
        "src.ui.pyqt_app.api_client.ApiClient.get_network_status",
        lambda self: {"message": "网络连接正常"},
    )

    window = MainWindow()
    app.processEvents()

    assert window.network_status_label.text().startswith("网络状态:")
    assert window.refresh_network_status_button.text() == "刷新"

    window.close()


def test_refresh_network_status_updates_label_from_payload(monkeypatch) -> None:
    app = qt_app()
    monkeypatch.setattr("src.ui.pyqt_app.main_window.network_available", lambda: True)
    monkeypatch.setattr(
        "src.ui.pyqt_app.api_client.ApiClient.get_network_status",
        lambda self: {"message": "网络连接正常"},
    )

    window = MainWindow()
    window.api_client = _NetworkApiStub(
        {
            "online": False,
            "checked_at": "2026-05-06T00:00:00+00:00",
            "probe_target": "1.1.1.1:53",
            "latency_ms": None,
            "message": "当前未联网",
        }
    )

    window.refresh_network_status()
    app.processEvents()

    assert window.network_status_label.text() == "网络状态: 当前未联网"

    window.close()
