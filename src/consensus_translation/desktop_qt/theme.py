from __future__ import annotations

import os

from PySide6.QtWidgets import QApplication


def _dark_mode_enabled() -> bool:
    return os.environ.get("CONSENSUS_TRANSLATION_DARK_MODE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def application_stylesheet(dark: bool = False) -> str:
    if dark:
        return """
            QMainWindow, QWidget { background: #202124; color: #f1f3f4; }
            #sideNavigation { background: #17181b; border: 0; padding: 8px; }
            #sideNavigation::item { padding: 10px 12px; border-radius: 6px; }
            #sideNavigation::item:selected { background: #2f5f9f; color: #ffffff; }
            #topBar { background: #26282d; border-bottom: 1px solid #3a3d45; }
            #appTitle { font-size: 18px; font-weight: 600; }
            #appSubtitle { color: #bdc1c6; }
            #pageTitle { font-size: 22px; font-weight: 600; }
        """
    return """
        QMainWindow, QWidget { background: #f7f8fa; color: #202124; }
        #sideNavigation { background: #ffffff; border: 0; border-right: 1px solid #dde1e6; padding: 8px; }
        #sideNavigation::item { padding: 10px 12px; border-radius: 6px; }
        #sideNavigation::item:selected { background: #e7f0ff; color: #174ea6; }
        #topBar { background: #ffffff; border-bottom: 1px solid #dde1e6; }
        #appTitle { font-size: 18px; font-weight: 600; }
        #appSubtitle { color: #5f6368; }
        #pageTitle { font-size: 22px; font-weight: 600; }
    """


def apply_application_theme(app: QApplication) -> None:
    app.setStyleSheet(application_stylesheet(_dark_mode_enabled()))
