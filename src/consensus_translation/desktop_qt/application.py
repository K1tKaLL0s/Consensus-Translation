from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from consensus_translation.desktop_qt.main_window import MainWindow
from consensus_translation.desktop_qt.theme import apply_application_theme


APPLICATION_NAME = "共识翻译 Agent"
ORGANIZATION_NAME = "ConsensusTranslation"
HEADLESS_FLAGS = frozenset({"--diagnostics", "--local-smoke"})


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


def _is_headless_cli(argv: Sequence[str]) -> bool:
    return any(argument in HEADLESS_FLAGS for argument in argv)


def _run_headless_cli(argv: Sequence[str]) -> int:
    from consensus_translation.desktop_agent_app import main as desktop_agent_main

    return desktop_agent_main(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if _is_headless_cli(args):
        return _run_headless_cli(args)

    app = create_application([sys.argv[0], *args])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
