import os
from pathlib import Path


def pytest_configure(config):
    root = Path(__file__).resolve().parents[1]
    isolated = Path(
        os.environ.get(
            "CONSENSUS_TEST_LOCALAPPDATA",
            root / ".pytest_localappdata" / "automatic",
        )
    ).resolve()
    isolated.mkdir(parents=True, exist_ok=True)
    os.environ["LOCALAPPDATA"] = str(isolated)
