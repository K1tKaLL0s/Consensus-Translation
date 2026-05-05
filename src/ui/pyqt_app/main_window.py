import socket

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QSplitter


def offline_notice_text() -> str:
    return "当前未联网，部分功能受限。"


def network_available(timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=timeout):
            return True
    except OSError:
        return False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MAATCS 三联屏控制台")

        splitter = QSplitter()
        splitter.addWidget(QLabel("左屏: 任务摄取舱"))
        splitter.addWidget(QLabel("中屏: 共识大厅"))
        splitter.addWidget(QLabel("右屏: 资产管理矩阵"))

        self.setCentralWidget(splitter)
        self.statusBar().showMessage("就绪")

        if not network_available():
            warning = offline_notice_text()
            self.statusBar().showMessage(warning)
            QMessageBox.information(self, "网络状态", warning)


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 700)
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
