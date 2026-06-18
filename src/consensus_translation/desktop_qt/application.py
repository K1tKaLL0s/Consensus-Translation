from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from consensus_translation.desktop_qt.main_window import MainWindow
from consensus_translation.desktop_qt.theme import apply_application_theme


APPLICATION_NAME = "共识翻译 Agent"
ORGANIZATION_NAME = "ConsensusTranslation"


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        app = existing
    else:
        app = QApplication(list(argv or []))

    app.setOrganizationName(ORGANIZATION_NAME)
    app.setOrganizationDomain("consensus-translation.local")
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationDisplayName(APPLICATION_NAME)
    apply_application_theme(app)
    return app


def main(argv: Sequence[str] | None = None) -> int:
    app = create_application(argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
