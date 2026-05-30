from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.database.neo4j_client import Neo4jClient
from src.repositories.case_repository import CaseRepository
from src.repositories.folder_repository import FolderRepository


class CasesBrowserView(QWidget):
    """
    Widget representing view in which folders and crime cases are presented.
    """

    ITEM_TYPE_ROLE = Qt.ItemDataRole.UserRole
    ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, BASE_DIR: Path) -> None:
        super().__init__()
        client = Neo4jClient()
        self.folder_repository = FolderRepository(client)
        self.case_repository = CaseRepository(client)
        self.BASE_DIR = BASE_DIR
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Cases")
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)

        label = QLabel("Cases Browser")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        add_folder_button = QPushButton("Add Folder")
        add_folder_button.clicked.connect(self.add_folder)
        button_layout.addWidget(add_folder_button)
        add_case_button = QPushButton("Add Case")
        add_case_button.clicked.connect(self.add_case)
        button_layout.addWidget(add_case_button)
        layout.addWidget(label)
        layout.addLayout(button_layout)
        layout.addWidget(self.tree)

        self.setLayout(layout)

    def style_item(self, item: QTreeWidgetItem) -> None:
        t = item.data(0, Qt.ItemDataRole.UserRole)

        if t == "folder":
            item.setIcon(
                0, QIcon(str(self.BASE_DIR / "src" / "assets" / "icons" / "folder.png"))
            )

        elif t == "case":
            item.setIcon(
                0, QIcon(str(self.BASE_DIR / "src" / "assets" / "icons" / "case.png"))
            )

    def open_menu(self, position: QPoint) -> None:
        item = self.tree.itemAt(position)
        if item:
            self.tree.setCurrentItem(item)

        menu = QMenu(self)

        if item is None:
            menu.addAction("Add Folder", self.add_folder)
            menu.addAction("Add Case", self.add_case)

        else:
            item_type = item.data(0, Qt.ItemDataRole.UserRole)

            if item_type == "folder":
                menu.addAction("Add Case", self.add_case)
                menu.addAction("Add Folder", self.add_folder)

            menu.addAction("Rename", lambda: self.rename_item(item))
            menu.addAction("Delete", lambda: self.delete_item(item))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def add_folder(self) -> None:
        """
        Adds folder with given name to the folder with given name in the tree widget.
        """
        ui_selected_item = self.tree.currentItem()

        name, ok = QInputDialog.getText(self, "Add Folder", "Folder name:")
        if not ok or not name:
            return

        parent_item = ui_selected_item

        # if CASE selected then go up
        if parent_item and parent_item.data(0, self.ITEM_TYPE_ROLE) == "case":
            parent_item = parent_item.parent()

        # if parent_item is QTreeWidget then in database we want to add folder
        # to root folder
        if parent_item is None:
            parent_folder = self.folder_repository.get_root_folder()
        else:
            parent_folder = self.folder_repository.get_folder(
                parent_item.data(0, self.ITEM_ID_ROLE)
            )

        # create folder in database and get its object representation
        folder = self.folder_repository.create_folder(
            parent_folder.id,
            name,
        )

        # create UI item for the folder and set its properties
        ui_item = QTreeWidgetItem([folder.name])

        ui_item.setData(0, self.ITEM_TYPE_ROLE, "folder")
        ui_item.setData(0, self.ITEM_ID_ROLE, folder.id)

        self.style_item(ui_item)

        # if parent_item is None, it means that we want to add folder to the root of
        # the tree widget, so we add it as top level item, otherwise
        # we add it as child of the parent item
        if parent_item is None:
            self.tree.addTopLevelItem(ui_item)
        else:
            parent_item.addChild(ui_item)

    def add_case(self) -> None:
        current = self.tree.currentItem()

        name, ok = QInputDialog.getText(self, "Add Case", "Case name:")
        if not ok or not name:
            return

        parent_item = current

        if parent_item is not None:
            item_type = parent_item.data(0, self.ITEM_TYPE_ROLE)

            # if CASE selected then go up to folder
            if item_type == "case":
                parent_item = parent_item.parent()

        if parent_item is None:
            root_folder = self.folder_repository.get_root_folder()
            parent_folder_id = root_folder.id
        else:
            parent_folder_id = parent_item.data(0, self.ITEM_ID_ROLE)

        case = self.case_repository.create_case(
            parent_folder_id,
            name,
        )

        new_case = QTreeWidgetItem([case.name])

        new_case.setData(0, self.ITEM_TYPE_ROLE, "case")
        new_case.setData(0, self.ITEM_ID_ROLE, case.id)

        self.style_item(new_case)

        if parent_item is None:
            self.tree.addTopLevelItem(new_case)
        else:
            parent_item.addChild(new_case)

    def rename_item(self, item: QTreeWidgetItem) -> None:
        """
        Renames given item in the tree widget to the given name.
        """

        if item.data(0, self.ITEM_TYPE_ROLE) == "folder":
            folder_id = item.data(0, self.ITEM_ID_ROLE)
            if folder_id is not None:
                new_name, ok = QInputDialog.getText(self, "Rename Folder", "New name:")
                if ok and new_name:
                    self.folder_repository.rename_folder(folder_id, new_name)
                    item.setText(0, new_name)
        elif item.data(0, self.ITEM_TYPE_ROLE) == "case":
            case_id = item.data(0, self.ITEM_ID_ROLE)
            if case_id is not None:
                new_name, ok = QInputDialog.getText(self, "Rename Case", "New name:")
                if ok and new_name:
                    self.case_repository.rename_case(case_id, new_name)
                    item.setText(0, new_name)

    def delete_item(self, item: QTreeWidgetItem) -> None:
        """
        Deletes given item from the tree widget and database.
        If item is folder, deletes all its subfolders and cases as well.
        """

        reply = QMessageBox.question(self, "Delete", "Are you sure?")
        if reply == QMessageBox.StandardButton.No:
            return
        item_type = item.data(0, self.ITEM_TYPE_ROLE)
        item_id = item.data(0, self.ITEM_ID_ROLE)

        # delete from database
        if item_type == "folder":
            self.folder_repository.delete_folder(item_id)
        elif item_type == "case":
            self.case_repository.delete_case(item_id)

        # delete from UI
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(index)

    def load_data(self) -> None:
        """
        Loads folders and cases from the database and builds tree widget.
        """
        self.tree.clear()

        root_folder = self.folder_repository.get_root_folder()

        children_folders = self.folder_repository.get_children(root_folder.id)
        children_cases = self.case_repository.get_cases_in_folder(root_folder.id)

        # folders
        for folder in children_folders:
            item = self._build_folder_item(folder)
            self.tree.addTopLevelItem(item)

        # cases (ROOT-level cases)
        for case in children_cases:
            item = QTreeWidgetItem([case.name])

            item.setData(0, self.ITEM_TYPE_ROLE, "case")
            item.setData(0, self.ITEM_ID_ROLE, case.id)

            self.style_item(item)

            self.tree.addTopLevelItem(item)

    def _build_folder_item(self, folder) -> QTreeWidgetItem:
        """
        Builds tree widget item for given folder and its children folders
        and cases recursively.
        """
        item = QTreeWidgetItem([folder.name])

        item.setData(0, self.ITEM_TYPE_ROLE, "folder")
        item.setData(0, self.ITEM_ID_ROLE, folder.id)

        self.style_item(item)

        # subfolders
        for subfolder in self.folder_repository.get_children(folder.id):
            item.addChild(self._build_folder_item(subfolder))

        # cases inside folder
        for case in self.case_repository.get_cases_in_folder(folder.id):
            case_item = QTreeWidgetItem([case.name])

            case_item.setData(0, self.ITEM_TYPE_ROLE, "case")
            case_item.setData(0, self.ITEM_ID_ROLE, case.id)

            self.style_item(case_item)

            item.addChild(case_item)

        return item
