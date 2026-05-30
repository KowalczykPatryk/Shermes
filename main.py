import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.database.neo4j_client import Neo4jClient
from src.repositories.folder_repository import FolderRepository
from src.ui.main_window import MainWindow
from src.utils.utils import load_stylesheet

if __name__ == "__main__":

    MAIN_WINDOW_TITLE = "Shermes"
    MAIN_WINDOW_WIDTH = 1000
    MAIN_WINDOW_HEIGHT = 600
    DARK_MODE_DEFAULT = False

    BASE_DIR = Path(__file__).resolve().parent

    FolderRepository(Neo4jClient()).create_root_folder()

    app = QApplication(sys.argv)
    if DARK_MODE_DEFAULT:
        app.setStyleSheet(
            load_stylesheet(str(BASE_DIR / "src" / "styles" / "themes" / "dark.qss"))
        )
    else:
        app.setStyleSheet(
            load_stylesheet(str(BASE_DIR / "src" / "styles" / "themes" / "light.qss"))
        )

    window = MainWindow(app, BASE_DIR, dark_mode=DARK_MODE_DEFAULT)
    window.setWindowTitle(MAIN_WINDOW_TITLE)
    window.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
    window.show()

    sys.exit(app.exec())
