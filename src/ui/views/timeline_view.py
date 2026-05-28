from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class TimelineView(QWidget):
    """
    Widget representing view in which timeline is presented.
    """

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        label = QLabel("Timeline")

        layout.addWidget(label)

        self.setLayout(layout)
