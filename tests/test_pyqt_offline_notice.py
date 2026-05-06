import inspect

import src.ui.pyqt_app.main_window as main_window


def qt_app():
    import os
    from PyQt6.QtWidgets import QApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


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


def test_main_window_builds_interactive_tabs_instead_of_static_splitter(monkeypatch) -> None:
    source = inspect.getsource(main_window.MainWindow)

    assert hasattr(main_window.MainWindow, "build_interactive_tabs")
    assert "QTabWidget" in source
    assert "build_interactive_tabs" in source
    assert "QSplitter" not in source


def test_offline_notice_is_non_blocking_and_status_warning_set(monkeypatch) -> None:
    app = qt_app()
    warning = main_window.offline_notice_text()

    monkeypatch.setattr(main_window, "network_available", lambda: False)

    def fail_if_modal_information_called(*args, **kwargs):
        raise AssertionError("modal QMessageBox.information should not be used")

    monkeypatch.setattr(main_window.QMessageBox, "information", fail_if_modal_information_called)

    window = main_window.MainWindow()
    app.processEvents()

    assert window.statusBar().currentMessage() == warning
    assert hasattr(window, "offline_notice_box")
    assert window.offline_notice_box.isModal() is False

    window.offline_notice_box.close()
    window.close()
