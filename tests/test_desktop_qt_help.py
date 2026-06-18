import os
from pathlib import Path
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtCore import Qt

from consensus_translation.desktop_qt.main_window import MainWindow


def test_help_page_searches_packaged_topics(qtbot, tmp_path):
    window = MainWindow(data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    page = window.page("帮助中心")

    page.search_input.setText("Textractor")
    qtbot.mouseClick(page.search_button, Qt.LeftButton)

    assert page.results_list.count() >= 1
    assert page.results_list.item(0).text().startswith("连接器")
    assert "Textractor" in page.content_view.toPlainText()


def test_connectors_page_captures_folder_inbox(qtbot, tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    inbox.joinpath("scene.txt").write_text("こんにちは", encoding="utf-8")
    window = MainWindow(data_root=tmp_path)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    page = window.page("输入连接器")
    page.folder_path_input.setText(str(inbox))

    qtbot.mouseClick(page.capture_button, Qt.LeftButton)

    assert page.capture_list.count() == 1
    assert "こんにちは" in page.content_preview.toPlainText()
