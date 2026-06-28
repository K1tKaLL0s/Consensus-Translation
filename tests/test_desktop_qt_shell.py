import os
from pathlib import Path
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from consensus_translation.desktop_qt.application import create_application
from consensus_translation.desktop_qt.main_window import MainWindow
from consensus_translation.desktop_qt.navigation import NAVIGATION_LABELS


def test_main_window_exposes_release_navigation(qtbot, tmp_path):
    app = create_application([])
    window = MainWindow(controller=None, data_root=tmp_path)
    qtbot.addWidget(window)

    assert app.organizationName() == "ConsensusTranslation"
    assert app.applicationName() == window.windowTitle()
    assert window.navigation_labels() == list(NAVIGATION_LABELS)
    assert "历史" in window.navigation_labels()
    assert "设置" in window.navigation_labels()
