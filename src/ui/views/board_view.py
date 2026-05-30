from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.database.neo4j_client import Neo4jClient


class BoardView(QWidget):
    """
    Widget representing view in which investigation board is presented.
    """

    def __init__(self, BASE_DIR: Path) -> None:
        super().__init__()
        self.neo4j_client = Neo4jClient()
        self.BASE_DIR = BASE_DIR

        layout = QVBoxLayout()

        label = QLabel("Investigation Board")

        layout.addWidget(label)

        self.setLayout(layout)
