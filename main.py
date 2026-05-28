import sys

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow

if __name__ == "__main__":

    MAIN_WINDOW_TITLE = "Shermes"
    MAIN_WINDOW_WIDTH = 1000
    MAIN_WINDOW_HEIGHT = 600

    app = QApplication(sys.argv)

    window = MainWindow()
    window.setWindowTitle(MAIN_WINDOW_TITLE)
    window.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
    window.show()

    sys.exit(app.exec())
