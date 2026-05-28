from PySide6.QtWidgets import (
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


class MainWindow(QMainWindow):
    """
    Main window of the application and it contains stacked widget with all views.
    """

    def __init__(self):
        super().__init__()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        self.sidebar = QFrame()
        self.sidebar.setVisible(False)

        self.toggle_button = QPushButton("☰")
        self.toggle_button.setFixedSize(30, 30)
        self.sidebar_wrapper = QWidget()
        self.sidebar_wrapper_layout = QVBoxLayout(self.sidebar_wrapper)
        self.sidebar_wrapper_layout.addWidget(self.toggle_button)
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

        self.cases_browser_view = CasesBrowserView()
        self.board_view = BoardView()
        self.timeline_view = TimelineView()

        self.stack.addWidget(self.cases_browser_view)
        self.stack.addWidget(self.board_view)
        self.stack.addWidget(self.timeline_view)

        self.stack.setCurrentWidget(self.cases_browser_view)

        main_layout.addWidget(self.sidebar_wrapper)
        main_layout.addWidget(self.stack)

    def show_board(self):
        """
        Switches widget in stacked widget to board view.
        """
        self.stack.setCurrentWidget(self.board_view)

    def show_timeline(self):
        """
        Switches widget in stacked widget to timeline view.
        """
        self.stack.setCurrentWidget(self.timeline_view)

    def show_cases_browser(self):
        """
        Switches widget in stacked widget to cases browser view.
        """
        self.stack.setCurrentWidget(self.cases_browser_view)
