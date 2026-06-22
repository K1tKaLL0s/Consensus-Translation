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


def test_main_window_exposes_release_navigation(qtbot, tmp_path):
    app = create_application([])
    window = MainWindow(controller=None, data_root=tmp_path)
    qtbot.addWidget(window)

    assert app.organizationName() == "ConsensusTranslation"
    assert app.applicationName() == "共识翻译 Agent"
    assert window.windowTitle() == "共识翻译 Agent"
    assert window.navigation_labels() == [
        "首页",
        "翻译工作台",
        "项目与任务",
        "词库与风格",
        "输入连接器",
        "Provider 与评估器",
        "诊断与运行时",
        "帮助中心",
    ]
