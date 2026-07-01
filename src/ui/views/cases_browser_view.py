"""Case tree which opens an investigation board on a case click."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal, Slot
from PySide6.QtGui import QIcon, QMouseEvent
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
    """Folders and cases. Clicking a case asks the main window to open it."""

    # This signals are connected to slots in the main window, which then call the
    # appropriate methods.
    case_open_requested = Signal(str, str)
    case_renamed = Signal(str, str)
    case_deleted = Signal(str)

    ITEM_TYPE_ROLE = Qt.ItemDataRole.UserRole
    ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 1

    def __init__(self, BASE_DIR: Path) -> None:
        super().__init__()
        client = Neo4jClient()
        self.folder_repository = FolderRepository(client)
        self.case_repository = CaseRepository(client)
        self.base_dir = BASE_DIR

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Cases")
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.viewport().installEventFilter(self)

        label = QLabel("Cases Browser")
        label.setObjectName("casesBrowserLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        add_folder_button = QPushButton("Add Folder")
        add_folder_button.clicked.connect(self.add_folder)
        add_case_button = QPushButton("Add Case")
        add_case_button.clicked.connect(self.add_case)
        button_layout = QHBoxLayout()
        button_layout.addWidget(add_folder_button)
        button_layout.addWidget(add_case_button)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addLayout(button_layout)
        layout.addWidget(self.tree)

    def eventFilter(
        self,
        obj: QObject,
        event: QEvent,
    ) -> bool:  # noqa: N802 - Qt API name
        """Clear selection when clicking on empty space in the tree view."""
        if (
            obj == self.tree.viewport()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
        ):
            clicked_item = self.tree.itemAt(event.position().toPoint())

            if clicked_item is None:
                self.tree.clearSelection()
                self.tree.selectionModel().clearCurrentIndex()

        return super().eventFilter(obj, event)

    def style_item(self, item: QTreeWidgetItem) -> None:
        """Set the icon for a tree item based on its type."""
        item_type = item.data(0, self.ITEM_TYPE_ROLE)
        if item_type == "folder":
            icon_path = self.base_dir / "src" / "assets" / "icons" / "folder.png"
        elif item_type == "case":
            icon_path = self.base_dir / "src" / "assets" / "icons" / "case.png"
        else:
            return
        item.setIcon(0, QIcon(str(icon_path)))

    def open_menu(self, position: QPoint) -> None:
        """Open a context menu for the tree view."""
        item = self.tree.itemAt(position)
        if item:
            self.tree.setCurrentItem(item)

        menu = QMenu(self)
        if item is None:
            menu.addAction("Add Folder", self.add_folder)
            menu.addAction("Add Case", self.add_case)
        else:
            item_type = item.data(0, self.ITEM_TYPE_ROLE)
            if item_type == "folder":
                menu.addAction("Add Case", self.add_case)
                menu.addAction("Add Folder", self.add_folder)
            elif item_type == "case":
                menu.addAction("Open board", lambda: self.open_case(item))
                menu.addSeparator()
            menu.addAction("Rename", lambda: self.rename_item(item))
            menu.addAction("Delete", lambda: self.delete_item(item))
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def add_folder(self) -> None:
        """Add a new folder under the selected folder or root."""
        selected = self.tree.currentItem()
        name, accepted = QInputDialog.getText(self, "Add Folder", "Folder name:")
        name = name.strip()
        if not accepted or not name:
            return

        parent_item = selected
        if parent_item and parent_item.data(0, self.ITEM_TYPE_ROLE) == "case":
            parent_item = parent_item.parent()

        if parent_item is None:
            parent_folder_id = self.folder_repository.get_root_folder().id
        else:
            parent_folder_id = parent_item.data(0, self.ITEM_ID_ROLE)

        try:
            folder = self.folder_repository.create_folder(parent_folder_id, name)
        except Exception as error:
            QMessageBox.critical(self, "Could not add folder", str(error))
            return

        item = QTreeWidgetItem([folder.name])
        item.setData(0, self.ITEM_TYPE_ROLE, "folder")
        item.setData(0, self.ITEM_ID_ROLE, folder.id)
        self.style_item(item)
        if parent_item is None:
            self.tree.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
            parent_item.setExpanded(True)

    def add_case(self) -> None:
        """Add a new case under the selected folder or root."""
        selected = self.tree.currentItem()
        name, accepted = QInputDialog.getText(self, "Add Case", "Case name:")
        name = name.strip()
        if not accepted or not name:
            return

        parent_item = selected
        if (
            parent_item is not None
            and parent_item.data(0, self.ITEM_TYPE_ROLE) == "case"
        ):
            parent_item = parent_item.parent()

        if parent_item is None:
            folder_id = self.folder_repository.get_root_folder().id
        else:
            folder_id = parent_item.data(0, self.ITEM_ID_ROLE)

        try:
            case = self.case_repository.create_case(folder_id, name)
        except Exception as error:
            QMessageBox.critical(self, "Could not add case", str(error))
            return

        item = QTreeWidgetItem([case.name])
        item.setData(0, self.ITEM_TYPE_ROLE, "case")
        item.setData(0, self.ITEM_ID_ROLE, case.id)
        self.style_item(item)
        if parent_item is None:
            self.tree.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
            parent_item.setExpanded(True)

    def rename_item(self, item: QTreeWidgetItem) -> None:
        """
        Rename a folder or case.
        The slot that receives this signal is connected in the main window.
        """
        item_type = item.data(0, self.ITEM_TYPE_ROLE)
        item_id = item.data(0, self.ITEM_ID_ROLE)
        if not item_id:
            return
        title = "Rename Folder" if item_type == "folder" else "Rename Case"
        new_name, accepted = QInputDialog.getText(
            self, title, "New name:", text=item.text(0)
        )
        new_name = new_name.strip()
        if not accepted or not new_name:
            return

        try:
            if item_type == "folder":
                self.folder_repository.rename_folder(item_id, new_name)
            elif item_type == "case":
                self.case_repository.rename_case(item_id, new_name)
            else:
                return
        except Exception as error:
            QMessageBox.critical(self, "Could not rename item", str(error))
            return

        item.setText(0, new_name)
        if item_type == "case":
            self.case_renamed.emit(item_id, new_name)

    def delete_item(self, item: QTreeWidgetItem) -> None:
        """
        Delete a folder or case after confirmation.
        The slot that receives this signal is connected in the main window.
        """
        item_type = item.data(0, self.ITEM_TYPE_ROLE)
        item_id = item.data(0, self.ITEM_ID_ROLE)
        if not item_id:
            return
        reply = QMessageBox.question(
            self,
            "Delete",
            "Delete this item? Deleting a folder also deletes its "
            + "subfolders, cases and case boards.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_case_ids = (
            self._case_ids_in_subtree(item) if item_type == "folder" else [item_id]
        )
        try:
            if item_type == "folder":
                self.folder_repository.delete_folder(item_id)
            elif item_type == "case":
                self.case_repository.delete_case(item_id)
            else:
                return
        except Exception as error:
            QMessageBox.critical(self, "Could not delete item", str(error))
            return

        for case_id in deleted_case_ids:
            self.case_deleted.emit(case_id)
        parent = item.parent()
        if parent is None:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))
        else:
            parent.removeChild(item)

    def open_case(self, item: QTreeWidgetItem) -> None:
        """
        Emit a signal to open the case board for the clicked case.
        The slot that receives this signal is connected in the main window.
        """
        if item.data(0, self.ITEM_TYPE_ROLE) != "case":
            return
        case_id = item.data(0, self.ITEM_ID_ROLE)
        if case_id:
            self.case_open_requested.emit(case_id, item.text(0))

    def load_data(self) -> None:
        """Load the folder and case tree from the database."""
        self.tree.clear()
        try:
            root_folder = self.folder_repository.get_root_folder()
            for folder in self.folder_repository.get_children(root_folder.id):
                self.tree.addTopLevelItem(self._build_folder_item(folder))
            for case in self.case_repository.get_cases_in_folder(root_folder.id):
                self.tree.addTopLevelItem(self._build_case_item(case.id, case.name))
        except Exception as error:
            QMessageBox.critical(self, "Could not load cases", str(error))

    @Slot(QTreeWidgetItem, int)
    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """
        Open the case board when a case is clicked.
        This slot is connected to the tree's itemClicked signal
        which is instance of SignalInstance
        """
        self.open_case(item)

    def _case_ids_in_subtree(self, item: QTreeWidgetItem) -> list[str]:
        """Return case ids represented by a tree item and all of its descendants."""
        case_ids: list[str] = []
        if item.data(0, self.ITEM_TYPE_ROLE) == "case":
            case_id = item.data(0, self.ITEM_ID_ROLE)
            if case_id:
                case_ids.append(case_id)
        for index in range(item.childCount()):
            case_ids.extend(self._case_ids_in_subtree(item.child(index)))
        return case_ids

    def _build_folder_item(self, folder) -> QTreeWidgetItem:
        """Recursively build a QTreeWidgetItem for a folder and its children."""
        item = QTreeWidgetItem([folder.name])
        item.setData(0, self.ITEM_TYPE_ROLE, "folder")
        item.setData(0, self.ITEM_ID_ROLE, folder.id)
        self.style_item(item)

        for child in self.folder_repository.get_children(folder.id):
            item.addChild(self._build_folder_item(child))
        for case in self.case_repository.get_cases_in_folder(folder.id):
            item.addChild(self._build_case_item(case.id, case.name))
        return item

    def _build_case_item(self, case_id: str, name: str) -> QTreeWidgetItem:
        """Build a QTreeWidgetItem for a case."""
        item = QTreeWidgetItem([name])
        item.setData(0, self.ITEM_TYPE_ROLE, "case")
        item.setData(0, self.ITEM_ID_ROLE, case_id)
        self.style_item(item)
        return item
