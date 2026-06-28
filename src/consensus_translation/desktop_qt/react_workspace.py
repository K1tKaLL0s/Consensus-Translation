from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from consensus_translation.desktop_qt.application_service import DesktopApplicationService
from consensus_translation.desktop_qt.react_bridge import ReactContractBridge


REACT_UI_RELATIVE_INDEX = (
    "UI design",
    "High-Fidelity Translation Software UI",
    "dist",
    "index.html",
)


def resolve_react_dist_index(project_root: str | Path | None = None) -> Path:
    packaged_index = _packaged_react_dist_index()
    if packaged_index is not None:
        return packaged_index
    root = Path(project_root).resolve() if project_root is not None else Path(__file__).resolve().parents[3]
    return root.joinpath(*REACT_UI_RELATIVE_INDEX)


def _packaged_react_dist_index() -> Path | None:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(str(meipass)) / "react-ui-dist" / "index.html")
    executable = Path(sys.executable).resolve()
    candidates.append(executable.parent / "_internal" / "react-ui-dist" / "index.html")
    candidates.append(executable.parent / "react-ui-dist" / "index.html")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def react_dist_status(project_root: str | Path | None = None) -> dict[str, str]:
    index_path = resolve_react_dist_index(project_root)
    return {
        "status": "available" if index_path.is_file() else "missing",
        "path": str(index_path),
    }


class ReactWorkspacePage(QWidget):
    """Desktop host for the built React high-fidelity UI."""

    def __init__(
        self,
        service: DesktopApplicationService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.react_status = react_dist_status()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        index_path = Path(self.react_status["path"])
        if self.react_status["status"] != "available":
            label = QLabel(
                "React 工作区未构建。请先在 UI design/High-Fidelity Translation Software UI 中运行 npm run build。",
                self,
            )
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(label, 1)
            return

        try:
            from PySide6.QtWebChannel import QWebChannel
            from PySide6.QtWebEngineCore import QWebEngineScript
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except Exception as exc:  # noqa: BLE001 - optional desktop rendering surface.
            label = QLabel(f"React 工作区需要 QtWebEngine：{exc}", self)
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(label, 1)
            return

        self.web_view = QWebEngineView(self)
        self.bridge = ReactContractBridge(self.service)
        self.channel = QWebChannel(self.web_view.page())
        self.channel.registerObject("consensusBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        script = QWebEngineScript()
        script.setName("consensus-contract-bridge")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        script.setSourceCode(
            """
(function () {
  function startBridge() {
    if (!window.qt || !window.qt.webChannelTransport || !window.QWebChannel) {
      window.dispatchEvent(new Event("consensus-bridge-unavailable"));
      return;
    }
    new window.QWebChannel(window.qt.webChannelTransport, function (channel) {
      window.consensusTranslationBridge = channel.objects.consensusBridge;
      window.dispatchEvent(new Event("consensus-bridge-ready"));
    });
  }
  if (window.QWebChannel) {
    startBridge();
    return;
  }
  var script = document.createElement("script");
  script.src = "qrc:///qtwebchannel/qwebchannel.js";
  script.onload = startBridge;
  script.onerror = function () {
    window.dispatchEvent(new Event("consensus-bridge-unavailable"));
  };
  document.documentElement.appendChild(script);
})();
            """.strip()
        )
        self.web_view.page().scripts().insert(script)
        self.web_view.setUrl(QUrl.fromLocalFile(str(index_path)))
        layout.addWidget(self.web_view, 1)
