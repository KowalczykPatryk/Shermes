from pathlib import Path

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
    """
    Main window of the application and it contains stacked widget with all views.
    """

    TOGGLE_BUTTON_SIZE = 35
    DARK_MODE_EMOJI = "🌙"
    LIGHT_MODE_EMOJI = "☀️"
    TOGGLE_BUTTON_TEXT = "☰"

    def __init__(self, app: QApplication, BASE_DIR: Path, dark_mode: bool) -> None:
        super().__init__()
        self.app = app
        self.BASE_DIR = BASE_DIR

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        self.sidebar = QFrame()
        self.sidebar.setVisible(False)

        self.toggle_button = QPushButton(self.TOGGLE_BUTTON_TEXT)
        if dark_mode:
            self.toggle_theme_button = QPushButton(self.DARK_MODE_EMOJI)
        else:
            self.toggle_theme_button = QPushButton(self.LIGHT_MODE_EMOJI)

        self.toggle_theme_button.setFixedSize(
            self.TOGGLE_BUTTON_SIZE, self.TOGGLE_BUTTON_SIZE
        )

        self.toggle_theme_button.setCheckable(True)
        self.toggle_theme_button.toggled.connect(self.change_theme)
        self.toggle_buttons_layout = QHBoxLayout()
        self.toggle_buttons_layout.addWidget(self.toggle_button)
        self.toggle_buttons_layout.addWidget(self.toggle_theme_button)
        self.toggle_button.setFixedSize(
            self.TOGGLE_BUTTON_SIZE, self.TOGGLE_BUTTON_SIZE
        )
        self.sidebar_wrapper = QWidget()
        self.sidebar_wrapper_layout = QVBoxLayout(self.sidebar_wrapper)
        self.sidebar_wrapper_layout.addLayout(self.toggle_buttons_layout)
        self.sidebar_wrapper_layout.addWidget(self.sidebar)
        self.sidebar_wrapper_layout.addStretch()

        self.toggle_button.clicked.connect(
            lambda: (self.sidebar.setVisible(not self.sidebar.isVisible()))
        )

        sidebar_layout = QVBoxLayout(self.sidebar)
        board_button = QPushButton("Board")
        board_button.clicked.connect(self.show_board)
        sidebar_layout.addWidget(board_button)
        timeline_button = QPushButton("Timeline")
        timeline_button.clicked.connect(self.show_timeline)
        sidebar_layout.addWidget(timeline_button)
        cases_button = QPushButton("Cases")
        cases_button.clicked.connect(self.show_cases_browser)
        sidebar_layout.addWidget(cases_button)

        sidebar_layout.addStretch()

        self.stack = QStackedWidget()

        self.cases_browser_view = CasesBrowserView(self.BASE_DIR)
        self.board_view = BoardView()
        self.timeline_view = TimelineView()

        self.stack.addWidget(self.cases_browser_view)
        self.stack.addWidget(self.board_view)
        self.stack.addWidget(self.timeline_view)

        self.stack.setCurrentWidget(self.cases_browser_view)

        main_layout.addWidget(self.sidebar_wrapper)
        main_layout.addWidget(self.stack)

    def show_board(self) -> None:
        """
        Switches widget in stacked widget to board view.
        """
        self.stack.setCurrentWidget(self.board_view)

    def show_timeline(self) -> None:
        """
        Switches widget in stacked widget to timeline view.
        """
        self.stack.setCurrentWidget(self.timeline_view)

    def show_cases_browser(self) -> None:
        """
        Switches widget in stacked widget to cases browser view.
        """
        self.stack.setCurrentWidget(self.cases_browser_view)

    def change_theme(self, enabled: bool) -> None:
        """
        Toggles between light and dark theme.
        """
        # by default, light mode is enabled, so if enabled is true,
        # we want to switch to dark mode
        if enabled:
            set_theme(
                self.app, str(self.BASE_DIR / "src" / "styles" / "themes" / "dark.qss")
            )
        else:
            set_theme(
                self.app, str(self.BASE_DIR / "src" / "styles" / "themes" / "light.qss")
            )
        self.toggle_theme_button.setText(
            self.DARK_MODE_EMOJI if enabled else self.LIGHT_MODE_EMOJI
        )
