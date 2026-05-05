from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QSplitter


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MAATCS 三联屏控制台")

        splitter = QSplitter()
        splitter.addWidget(QLabel("左屏: 任务摄取舱"))
        splitter.addWidget(QLabel("中屏: 共识大厅"))
        splitter.addWidget(QLabel("右屏: 资产管理矩阵"))

        self.setCentralWidget(splitter)


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.resize(1200, 700)
    window.show()
    app.exec()
