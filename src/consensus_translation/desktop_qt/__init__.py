from __future__ import annotations

from pathlib import Path
import sys


def ensure_source_qt_packages() -> None:
    """Expose the E-drive source dependency target when running unpackaged."""

    root = Path(__file__).resolve().parents[3]
    dependency_root = root / ".runtime" / "python-packages-qt"
    if dependency_root.is_dir() and str(dependency_root) not in sys.path:
        sys.path.insert(0, str(dependency_root))


ensure_source_qt_packages()

__all__ = ["ensure_source_qt_packages"]
