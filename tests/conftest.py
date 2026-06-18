import os
from pathlib import Path
import sys
from importlib.util import find_spec


ROOT = Path(__file__).resolve().parents[1]
QT_PACKAGES = ROOT / ".runtime" / "python-packages-qt"
if QT_PACKAGES.is_dir() and str(QT_PACKAGES) not in sys.path:
    sys.path.insert(0, str(QT_PACKAGES))

pytest_plugins = ("pytestqt.plugin",) if find_spec("pytestqt.plugin") else ()


def pytest_configure(config):
    isolated = Path(
        os.environ.get(
            "CONSENSUS_TEST_LOCALAPPDATA",
            ROOT / ".pytest_localappdata" / "automatic",
        )
    ).resolve()
    isolated.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(isolated)
