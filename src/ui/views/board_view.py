from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class BoardView(QWidget):
    """
    Widget representing view in which investigation board is presented.
    """

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        label = QLabel("Investigation Board")

        layout.addWidget(label)

        self.setLayout(layout)
