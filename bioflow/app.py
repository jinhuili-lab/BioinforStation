import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from bioflow.ui.main_window import MainWindow

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    font = app.font()
    size = font.pointSize()
    if size <= 0:
        size = 10
    font.setPointSize(int(size * 1.25))
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
