from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QSplitter


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CN-JP Translator")

        splitter = QSplitter()
        splitter.addWidget(QLabel("左侧面板"))
        splitter.addWidget(QLabel("中间面板"))
        splitter.addWidget(QLabel("右侧面板"))

        self.setCentralWidget(splitter)


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 700)
    window.show()
    app.exec()
