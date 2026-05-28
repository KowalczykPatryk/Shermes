from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class CasesBrowserView(QWidget):
    """
    Widget representing view in which folders and crime cases are presented.
    """

    def __init__(self):
        super().__init__()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Cases")
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)

        label = QLabel("Cases Browser")
        label.setStyleSheet("font-size: 18px; font-weight: bold;")
        label.setAlignment(Qt.AlignCenter)

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

    def style_item(self, item):
        t = item.data(0, Qt.UserRole)

        if t == "folder":
            item.setIcon(0, QIcon("assets/icons/folder.png"))
            item.setBackground(0, QColor("#2b3a55"))
            item.setForeground(0, QColor("#d0e1ff"))

        elif t == "case":
            item.setIcon(0, QIcon("assets/icons/case.png"))
            item.setBackground(0, QColor("#3a2b2b"))
            item.setForeground(0, QColor("#ffd0d0"))

    def open_menu(self, position):
        item = self.tree.itemAt(position)
        if item:
            self.tree.setCurrentItem(item)

        menu = QMenu(self)

        if item is None:
            menu.addAction("Add Folder", self.add_folder)
            menu.addAction("Add Case", self.add_case)

        else:
            item_type = item.data(0, Qt.UserRole)

            if item_type == "folder":
                menu.addAction("Add Case", self.add_case)
                menu.addAction("Add Folder", self.add_folder)

            menu.addAction("Rename")
            menu.addAction("Delete")

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def add_folder(self):
        current = self.tree.currentItem()

        name, ok = QInputDialog.getText(self, "Add Folder", "Folder name:")
        if not ok or not name:
            return

        new_folder = QTreeWidgetItem([name])
        new_folder.setData(0, Qt.UserRole, "folder")
        self.style_item(new_folder)

        # if no item is selected then top level item
        if current is None:
            self.tree.addTopLevelItem(new_folder)
            return

        # if selected item is folder then add to it, else add to parent folder,
        # if no parent then top level item
        if current.data(0, Qt.UserRole) == "folder":
            current.addChild(new_folder)
        else:
            # if current item is case then add to its parent folder,
            # if no parent then top level item
            parent = current.parent()
            if parent is not None:
                parent.addChild(new_folder)
            else:
                self.tree.addTopLevelItem(new_folder)

    def add_case(self):
        """
        Adds case with given name to the folder with given name in the tree widget.
        """
        current = self.tree.currentItem()

        name, ok = QInputDialog.getText(self, "Add Case", "Case name:")
        if not ok or not name:
            return

        new_case = QTreeWidgetItem([name])
        new_case.setData(0, Qt.UserRole, "case")
        self.style_item(new_case)

        # if no item is selected then top level item
        if current is None:
            self.tree.addTopLevelItem(new_case)
            return

        if current.data(0, Qt.UserRole) == "folder":
            current.addChild(new_case)
        else:
            parent = current.parent()
            if parent:
                parent.addChild(new_case)
            else:
                self.tree.addTopLevelItem(new_case)
