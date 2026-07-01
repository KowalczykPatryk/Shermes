"""Main window coordinating selected cases, their board and their timeline."""

from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.views.board_view import BoardView
from src.ui.views.cases_browser_view import CasesBrowserView
from src.ui.views.timeline_view import TimelineView
from src.utils.utils import set_theme


class MainWindow(QMainWindow):
    """Application shell with a case-aware Board and Timeline."""

    TOGGLE_BUTTON_SIZE = 35
    DARK_MODE_EMOJI = "🌙"
    LIGHT_MODE_EMOJI = "☀️"
    TOGGLE_BUTTON_TEXT = "☰"

    def __init__(self, app: QApplication, BASE_DIR: Path, dark_mode: bool) -> None:
        super().__init__()
        self.app = app
        self.base_dir = BASE_DIR
        self.BASE_DIR = BASE_DIR

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.sidebar = QFrame()
        self.sidebar.setVisible(False)
        self.toggle_button = QPushButton(self.TOGGLE_BUTTON_TEXT)
        self.toggle_button.setFixedSize(
            self.TOGGLE_BUTTON_SIZE, self.TOGGLE_BUTTON_SIZE
        )
        self.toggle_button.clicked.connect(
            lambda: self.sidebar.setVisible(not self.sidebar.isVisible())
        )

        self.toggle_theme_button = QPushButton(
            self.DARK_MODE_EMOJI if dark_mode else self.LIGHT_MODE_EMOJI
        )
        self.toggle_theme_button.setFixedSize(
            self.TOGGLE_BUTTON_SIZE, self.TOGGLE_BUTTON_SIZE
        )
        self.toggle_theme_button.setCheckable(True)
        self.toggle_theme_button.setChecked(dark_mode)
        self.toggle_theme_button.toggled.connect(self.change_theme)

        toggle_layout = QHBoxLayout()
        toggle_layout.addWidget(self.toggle_button)
        toggle_layout.addWidget(self.toggle_theme_button)
        self.sidebar_wrapper = QWidget()
        sidebar_wrapper_layout = QVBoxLayout(self.sidebar_wrapper)
        sidebar_wrapper_layout.addLayout(toggle_layout)
        sidebar_wrapper_layout.addWidget(self.sidebar)
        sidebar_wrapper_layout.addStretch()

        sidebar_layout = QVBoxLayout(self.sidebar)
        board_button = QPushButton("Board")
        board_button.clicked.connect(self.show_board)
        timeline_button = QPushButton("Timeline")
        timeline_button.clicked.connect(self.show_timeline)
        cases_button = QPushButton("Cases")
        cases_button.clicked.connect(self.show_cases_browser)
        sidebar_layout.addWidget(board_button)
        sidebar_layout.addWidget(timeline_button)
        sidebar_layout.addWidget(cases_button)
        sidebar_layout.addStretch()

        self.stack = QStackedWidget()
        self.cases_browser_view = CasesBrowserView(self.base_dir)
        self.board_view = BoardView(self.base_dir)
        self.timeline_view = TimelineView(self.base_dir)

        self.cases_browser_view.case_open_requested.connect(self.open_case_board)
        self.cases_browser_view.case_renamed.connect(self.rename_open_case)
        self.cases_browser_view.case_deleted.connect(self.close_deleted_case)

        self.board_view.timeline_requested.connect(self.show_timeline)
        self.board_view.board_changed.connect(self.refresh_current_timeline)

        self.stack.addWidget(self.cases_browser_view)
        self.stack.addWidget(self.board_view)
        self.stack.addWidget(self.timeline_view)
        self.stack.setCurrentWidget(self.cases_browser_view)
        self.cases_browser_view.load_data()

        main_layout.addWidget(self.sidebar_wrapper)
        main_layout.addWidget(self.stack)

    @Slot(str, str)
    def open_case_board(self, case_id: str, case_name: str) -> None:
        """Open the clicked case and load only its graph."""
        self.board_view.load_case(case_id, case_name)
        self.timeline_view.load_case(case_id, case_name)
        self.stack.setCurrentWidget(self.board_view)

    @Slot(str, str)
    def rename_open_case(self, case_id: str, name: str) -> None:
        self.board_view.rename_current_case(case_id, name)
        self.timeline_view.rename_current_case(case_id, name)

    @Slot(str)
    def close_deleted_case(self, case_id: str) -> None:
        if case_id == self.board_view.current_case_id:
            self.board_view.unload_case()
            self.timeline_view.unload_case()
            self.stack.setCurrentWidget(self.cases_browser_view)

    @Slot()
    def refresh_current_timeline(self) -> None:
        if self.timeline_view.current_case_id == self.board_view.current_case_id:
            self.timeline_view.refresh()

    @Slot()
    def show_board(self) -> None:
        self.stack.setCurrentWidget(self.board_view)

    @Slot()
    def show_timeline(self) -> None:
        self.refresh_current_timeline()
        self.stack.setCurrentWidget(self.timeline_view)

    @Slot()
    def show_cases_browser(self) -> None:
        self.stack.setCurrentWidget(self.cases_browser_view)

    @Slot(bool)
    def change_theme(self, enabled: bool) -> None:
        theme_name = "dark.qss" if enabled else "light.qss"
        set_theme(
            self.app, str(self.base_dir / "src" / "styles" / "themes" / theme_name)
        )
        self.toggle_theme_button.setText(
            self.DARK_MODE_EMOJI if enabled else self.LIGHT_MODE_EMOJI
        )
