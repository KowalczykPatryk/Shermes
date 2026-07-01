"""Case-bound graph board with filtering and graph analysis."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from shutil import copy2
from typing import Callable
from uuid import uuid4

from PySide6.QtCore import QDateTime, QPoint, QRectF, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDesktopServices,
    QKeySequence,
    QPainter,
    QPixmap,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.database.neo4j_client import Neo4jClient
from src.models.board_node import BoardNode, BoardNodeDraft, BoardNodeType
from src.repositories.board_repository import BoardRepository
from src.ui.graphic_items.edge import Edge
from src.ui.graphic_items.node import Node

NODE_TYPE_OPTIONS: tuple[tuple[BoardNodeType, str], ...] = (
    (BoardNodeType.PHOTO, "Photo"),
    (BoardNodeType.NOTE, "Note"),
    (BoardNodeType.PERSON, "Person"),
    (BoardNodeType.EVENT, "Event"),
    (BoardNodeType.PLACE, "Place"),
    (BoardNodeType.TIMESTAMP, "Timestamp"),
    (BoardNodeType.LINK, "Link"),
    (BoardNodeType.PDF, "PDF"),
)

NODE_TYPE_LABELS: dict[BoardNodeType, str] = dict(NODE_TYPE_OPTIONS)


class BoardGraphicsView(QGraphicsView):
    """Graphics view with pointer-centred zoom and mouse shifting."""

    fit_requested = Signal()

    ZOOM_FACTOR = 1.15

    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)

        # Enable anti-aliasing for smoother rendering
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Set the drag mode to ScrollHandDrag for changing the view
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # Set the transformation anchor to the mouse position for zooming
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        # Set the resize anchor to the center of the view for resizing window
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # Set the viewport update mode to full viewport update
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        # Emit a custom context menu signal when the user right-clicks
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.fit_button = QPushButton("Fit", self.viewport())
        self.fit_button.setObjectName("fitBoardButton")
        self.fit_button.clicked.connect(self.fit_requested.emit)

        self.zoom_in_button = QPushButton("+", self.viewport())
        self.zoom_out_button = QPushButton("-", self.viewport())

        self.zoom_in_button.setObjectName("zoomInButton")
        self.zoom_out_button.setObjectName("zoomOutButton")

        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)

        self.board_title_paper = QLabel(self.viewport())
        self.board_title_paper.setObjectName("boardTitlePaper")

        original_pixmap = QPixmap("src/assets/icons/title_paper.png")

        BOARD_TITLE_PAPER_HEIGHT = 80
        BOARD_TITLE_PAPER_WIDTH = int(
            BOARD_TITLE_PAPER_HEIGHT
            / original_pixmap.height()
            * original_pixmap.width()
        )
        self.board_title_paper.setFixedSize(
            BOARD_TITLE_PAPER_WIDTH, BOARD_TITLE_PAPER_HEIGHT
        )

        scaled_pixmap = original_pixmap.scaled(
            self.board_title_paper.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.board_title_paper.setPixmap(scaled_pixmap)

        self.board_title_paper.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.board_title = QLabel("", self.board_title_paper)
        self.board_title.setFixedSize(BOARD_TITLE_PAPER_WIDTH, BOARD_TITLE_PAPER_HEIGHT)
        self.board_title.setContentsMargins(8, 8, 8, 8)
        self.board_title.setWordWrap(True)
        self.board_title.setObjectName("boardTitle")
        self.board_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.board_title.setGeometry(
            0,
            0,
            BOARD_TITLE_PAPER_WIDTH,
            BOARD_TITLE_PAPER_HEIGHT,
        )

        self.fit_button.adjustSize()
        self._position_overlay_buttons()

    def zoom_in(self) -> None:
        self.scale(self.ZOOM_FACTOR, self.ZOOM_FACTOR)

    def zoom_out(self) -> None:
        self.scale(1 / self.ZOOM_FACTOR, 1 / self.ZOOM_FACTOR)

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt API name
        if event.angleDelta().y() > 0:
            self.zoom_in()
        elif event.angleDelta().y() < 0:
            self.zoom_out()
        event.accept()

    def _position_overlay_buttons(self) -> None:
        """
        Position overlay buttons (like the "Fit" button) in
        the bottom-right corner of the viewport.
        """
        margin = 12

        offset = (self.fit_button.width() - self.zoom_in_button.width()) // 2

        self.board_title_paper.move(
            0,
            0,
        )

        self.fit_button.move(
            self.viewport().width() - self.fit_button.width() - margin,
            margin,
        )
        self.zoom_in_button.move(
            self.viewport().width() - self.zoom_in_button.width() - margin - offset,
            int(self.fit_button.y() + self.fit_button.height() + margin),
        )
        self.zoom_out_button.move(
            self.viewport().width() - self.zoom_out_button.width() - margin - offset,
            int(self.zoom_in_button.y() + self.zoom_in_button.height() + margin),
        )

    def resizeEvent(
        self,
        event: QResizeEvent,
    ) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._position_overlay_buttons()


class NodeEditorDialog(QDialog):
    """Editor for all typed board nodes and their optional evidence references."""

    def __init__(
        self,
        parent: QWidget,
        *,
        attachments_dir: Path,
        initial: BoardNode | None = None,
        default_type: BoardNodeType = BoardNodeType.NOTE,
    ) -> None:
        super().__init__(parent)

        self._attachments_dir = attachments_dir

        self.setWindowTitle("Edit board node" if initial else "Add board node")
        self.setMinimumWidth(520)

        self.type_combo = QComboBox()
        for node_type, label in NODE_TYPE_OPTIONS:
            self.type_combo.addItem(label, node_type.value)

        selected_type = initial.node_type if initial else default_type
        self.type_combo.setCurrentIndex(self.type_combo.findData(selected_type.value))

        self.title_input = QLineEdit(initial.title if initial else "")
        self.title_input.setPlaceholderText("Short, identifiable title")

        self.description_input = QPlainTextEdit(initial.description if initial else "")
        self.description_input.setPlaceholderText(
            "Notes, context, source details, address, or observations"
        )
        self.description_input.setMinimumHeight(110)

        self.attachments_input = QPlainTextEdit(
            "\n".join(initial.attachments) if initial else ""
        )
        self.attachments_input.setPlaceholderText(
            "One local file path or URL per line. "
            "References are stored; files are not copied into Neo4j."
        )
        self.attachments_input.setFixedHeight(80)

        self.browse_button = QPushButton("Add file...")
        self.browse_button.clicked.connect(self._browse_for_attachment)
        attachment_layout = QVBoxLayout()
        attachment_layout.setContentsMargins(0, 0, 0, 0)
        attachment_layout.addWidget(self.attachments_input)
        attachment_layout.addWidget(self.browse_button)
        attachment_widget = QWidget()
        attachment_widget.setLayout(attachment_layout)

        self.timestamp_enabled = QCheckBox("This node has a date and time")
        self.timestamp_edit = QDateTimeEdit()
        self.timestamp_edit.setCalendarPopup(True)
        self.timestamp_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.timestamp_edit.setDateTime(QDateTime.currentDateTime())

        if initial and initial.occurred_at:
            parsed = QDateTime.fromString(initial.occurred_at, Qt.DateFormat.ISODate)
            if parsed.isValid():
                self.timestamp_enabled.setChecked(True)
                self.timestamp_edit.setDateTime(parsed)
        self.timestamp_edit.setEnabled(self.timestamp_enabled.isChecked())
        self.timestamp_enabled.toggled.connect(self.timestamp_edit.setEnabled)

        form = QFormLayout()
        form.addRow("Type:", self.type_combo)
        form.addRow("Title:", self.title_input)
        form.addRow("Description:", self.description_input)
        form.addRow("Files and links:", attachment_widget)
        form.addRow("Timestamp:", self.timestamp_enabled)
        form.addRow("Date and time:", self.timestamp_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def draft(self) -> BoardNodeDraft:
        """Return a sanitised, validated model payload."""
        attachments = tuple(
            line.strip()
            for line in self.attachments_input.toPlainText().splitlines()
            if line.strip()
        )
        occurred_at = None
        if self.timestamp_enabled.isChecked():
            occurred_at = self.timestamp_edit.dateTime().toString(Qt.DateFormat.ISODate)

        return BoardNodeDraft(
            node_type=BoardNodeType(self.type_combo.currentData()),
            title=self.title_input.text().strip(),
            description=self.description_input.toPlainText().strip(),
            attachments=attachments,
            occurred_at=occurred_at,
        )

    @Slot()
    def _validate_and_accept(self) -> None:
        """Check that the title is not empty before accepting the dialog."""
        if not self.title_input.text().strip():
            QMessageBox.warning(
                self, "Missing title", "A board node must have a title."
            )
            self.title_input.setFocus()
            return
        self.accept()

    @Slot()
    def _browse_for_attachment(self) -> None:
        """Open a file dialog to select a local file to attach to the node."""
        node_type = BoardNodeType(self.type_combo.currentData())
        if node_type == BoardNodeType.PHOTO:
            file_filter = "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All files (*)"
        elif node_type == BoardNodeType.PDF:
            file_filter = "PDF documents (*.pdf);;All files (*)"
        else:
            file_filter = "All files (*)"

        path, _ = QFileDialog.getOpenFileName(self, "Attach file", "", file_filter)

        if not path:
            return

        try:
            stored_path = self._import_attachment(path)
        except OSError as error:
            QMessageBox.critical(
                self,
                "Could not import file",
                f"Could not copy the selected file:\n{error}",
            )
            return

        text = self.attachments_input.toPlainText().strip()
        self.attachments_input.setPlainText(
            f"{text}\n{stored_path}" if text else stored_path
        )

    def _import_attachment(self, source_path: str) -> str:
        """Copy a selected file into the application's managed attachment store."""
        source = Path(source_path)

        if not source.is_file():
            raise FileNotFoundError(f"Selected file does not exist: {source}")

        self._attachments_dir.mkdir(parents=True, exist_ok=True)

        target_name = f"{uuid4().hex}{source.suffix.lower()}"
        target = self._attachments_dir / target_name

        copy2(source, target)

        return target.relative_to(self._attachments_dir.parent.parent).as_posix()


class BoardView(QWidget):
    """Evidence graph for one selected case at a time."""

    timeline_requested = Signal()
    board_changed = Signal()

    SCENE_RECT = QRectF(0.0, 0.0, 3200.0, 2000.0)

    def __init__(self, BASE_DIR: Path) -> None:
        super().__init__()

        self._base_dir = BASE_DIR
        self._attachments_dir = BASE_DIR / "data" / "attachments"

        self.repository = BoardRepository(Neo4jClient())
        self.current_case_id: str | None = None
        self.current_case_name: str | None = None
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, Edge] = {}
        self._connection_mode = False
        self._connection_source: Node | None = None
        self._analysis_node_ids: set[str] = set()
        self._analysis_edge_ids: set[str] = set()

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(self.SCENE_RECT)
        self.scene.setBackgroundBrush(QBrush(QColor("#84542c")))

        self.view = BoardGraphicsView(self.scene, self)
        self.view.fit_requested.connect(self.fit_board)
        self.view.customContextMenuRequested.connect(self.open_context_menu)

        self.new_type_combo = QComboBox()
        for node_type, label in NODE_TYPE_OPTIONS:
            self.new_type_combo.addItem(label, node_type.value)

        self.add_node_button = QPushButton("Add node")
        self.add_node_button.clicked.connect(self.add_node_dialog)
        self.edit_button = QPushButton("Edit selected")
        self.edit_button.clicked.connect(self.edit_selected_node)
        self.delete_button = QPushButton("Delete selected")
        self.delete_button.clicked.connect(self.delete_selected_items)
        self.clear_button = QPushButton("Clear case board")
        self.clear_button.clicked.connect(self.clear_board)

        self.connect_button = QPushButton("Connect nodes")
        self.connect_button.clicked.connect(self.start_connection)
        self.shortest_path_button = QPushButton("Shortest path between people")
        self.shortest_path_button.clicked.connect(self.find_shortest_path)
        self.central_person_button = QPushButton("Most indirectly connected person")
        self.central_person_button.clicked.connect(
            self.find_most_indirectly_connected_person
        )

        self.clear_analysis_button = QPushButton("Clear analysis")
        self.clear_analysis_button.clicked.connect(self.clear_analysis)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All node types", None)
        for node_type, label in NODE_TYPE_OPTIONS:
            self.filter_combo.addItem(label, node_type.value)
        self.filter_combo.currentIndexChanged.connect(self.apply_filters)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search titles, notes, files, links, dates..."
        )
        self.search_input.textChanged.connect(self.apply_filters)
        self.clear_filter_button = QPushButton("Clear filters")
        self.clear_filter_button.clicked.connect(self.clear_filters)

        create_controls = QHBoxLayout()
        create_controls.setContentsMargins(0, 0, 0, 0)
        new_type_label = QLabel("New type:")
        new_type_label.setObjectName("newTypeLabel")
        create_controls.addWidget(new_type_label)
        create_controls.addWidget(self.new_type_combo)
        create_controls.addWidget(self.add_node_button)
        create_controls.addStretch()

        selected_controls = QHBoxLayout()
        selected_controls.setContentsMargins(0, 0, 0, 0)
        selected_controls.addWidget(self.edit_button)
        selected_controls.addWidget(self.delete_button)
        selected_controls.addWidget(self.connect_button)
        selected_controls.addStretch()

        analysis_controls = QHBoxLayout()
        analysis_controls.setContentsMargins(0, 0, 0, 0)
        analysis_controls.addWidget(self.shortest_path_button)
        analysis_controls.addWidget(self.central_person_button)
        analysis_controls.addStretch()

        clear_controls = QHBoxLayout()
        clear_controls.setContentsMargins(0, 0, 0, 0)
        clear_controls.addWidget(self.clear_analysis_button)
        clear_controls.addWidget(self.clear_button)
        clear_controls.addStretch()

        self.clear_button.setObjectName("clearCaseButton")

        create_group = self._make_control_group(
            "CREATE NODE",
            create_controls,
            "createControls",
        )

        selected_group = self._make_control_group(
            "SELECTED ITEMS",
            selected_controls,
            "selectedControls",
        )

        analysis_group = self._make_control_group(
            "GRAPH ANALYSIS",
            analysis_controls,
            "analysisControls",
        )

        clear_group = self._make_control_group(
            "CLEAR / RESET",
            clear_controls,
            "clearControls",
        )

        filter_controls = QHBoxLayout()
        filter_controls.addWidget(QLabel("Filter:"))
        filter_controls.addWidget(self.filter_combo)
        filter_controls.addWidget(self.search_input, 1)
        filter_controls.addWidget(self.clear_filter_button)

        self.status_label = QLabel("Select a case in Cases to open its board.")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(create_group)
        layout.addWidget(selected_group)
        layout.addWidget(analysis_group)
        layout.addWidget(clear_group)

        layout.addLayout(filter_controls)
        layout.addWidget(self.status_label)

        self.wooden_frame = QFrame()
        self.wooden_frame.setObjectName("woodFrame")

        wooden_frame_layout = QVBoxLayout(self.wooden_frame)
        wooden_frame_layout.setContentsMargins(0, 0, 0, 0)
        wooden_frame_layout.setSpacing(0)
        wooden_frame_layout.addWidget(self.view)

        layout.addWidget(self.wooden_frame, 1)

        self._case_required_widgets = (
            self.new_type_combo,
            self.add_node_button,
            self.edit_button,
            self.delete_button,
            self.clear_button,
            self.connect_button,
            self.shortest_path_button,
            self.central_person_button,
            self.clear_analysis_button,
            self.filter_combo,
            self.search_input,
            self.clear_filter_button,
        )
        self._set_case_controls_enabled(False)
        self._create_shortcuts()

        self._fit_pending = True
        self._request_fit_board()

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 - Qt API name
        """Fit the board only after this view becomes visible."""
        super().showEvent(event)

        if self._fit_pending:
            QTimer.singleShot(0, self._apply_pending_fit)

    def _request_fit_board(self) -> None:
        """Request a fit once the graphics viewport has a usable size."""
        self._fit_pending = True

        if self.isVisible():
            QTimer.singleShot(0, self._apply_pending_fit)

    def _apply_pending_fit(self) -> None:
        """Apply a requested fit only when the graphics view is visible."""
        if not self._fit_pending:
            return

        if not self.view.isVisible() or self.view.viewport().size().isEmpty():
            return

        self._fit_pending = False
        self.fit_board()

    def _make_control_group(
        self,
        title: str,
        controls: QHBoxLayout,
        object_name: str,
    ) -> QFrame:
        """Wrap one related set of board controls in a titled panel."""
        frame = QFrame()
        frame.setObjectName(object_name)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 8)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("boardControlGroupTitle")

        layout.addWidget(title_label)
        layout.addLayout(controls)

        return frame

    @property
    def nodes(self) -> tuple[Node, ...]:
        """Return a stable snapshot of incident nodes."""
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[Edge, ...]:
        """Return a stable snapshot of incident edges."""
        return tuple(self._edges.values())

    def load_case(self, case_id: str, case_name: str) -> None:
        """Load nodes, links and saved positions belonging only to one case."""
        self._clear_scene_items()
        self.current_case_id = case_id
        self.current_case_name = case_name
        self.view.board_title.setText(f"Case: {case_name}")
        self._set_case_controls_enabled(True)
        self.clear_filters()

        try:
            records = self.repository.get_nodes(case_id)
            for record in records:
                self._add_node_to_scene(record)

            for edge_record in self.repository.get_edges(case_id):
                source = self._nodes.get(edge_record.source_id)
                target = self._nodes.get(edge_record.target_id)
                if source is not None and target is not None:
                    self._add_edge_to_scene(edge_record.id, source, target)
        except Exception as error:
            self._clear_scene_items()
            self._show_error("Could not load this case board", error)
            return

        self.apply_filters()
        self._request_fit_board()
        self._set_status(
            f'Loaded "{case_name}": {len(self._nodes)} node(s),'
            f" {len(self._edges)} connection(s)."
        )

    def unload_case(self) -> None:
        """Clear the canvas when its currently loaded case is removed."""
        self._clear_scene_items()
        self.current_case_id = None
        self.current_case_name = None
        self.view.board_title.setText("Case: no case selected")
        self._set_case_controls_enabled(False)
        self._set_status("Select a case in Cases to open its board.")
        self._request_fit_board()

    def rename_current_case(self, case_id: str, name: str) -> None:
        """Keep the board header in sync with a renamed Case."""
        if case_id == self.current_case_id:
            self.current_case_name = name
            self.view.board_title.setText(f"Case: {name}")

    def add_node_dialog(self) -> None:
        """Create a typed node after collecting all information in one dialog."""
        case_id = self._require_case()
        if case_id is None:
            return
        default_type = BoardNodeType(self.new_type_combo.currentData())
        dialog = NodeEditorDialog(
            self,
            attachments_dir=self._attachments_dir,
            default_type=default_type,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.add_node_from_draft(dialog.draft())

    def add_node_from_draft(self, draft: BoardNodeDraft) -> Node | None:
        """Persist a new node, then render exactly the persisted representation."""
        case_id = self._require_case()
        if case_id is None:
            return None
        position = self._next_node_position()
        try:
            record = self.repository.create_node(
                case_id,
                draft,
                x=position[0],
                y=position[1],
            )
        except Exception as error:
            self._show_error("Could not create board node", error)
            return None

        node = self._add_node_to_scene(record)
        self.apply_filters()
        self._set_status(
            f"Added {NODE_TYPE_LABELS[record.node_type].lower()} "
            f'node: "{record.title}".'
        )
        self.board_changed.emit()
        return node

    def start_connection(self) -> None:
        """Enter a two-click mode for saving a relationship between two nodes."""
        case_id = self._require_case()
        if case_id is None:
            return
        self.cancel_connection(silent=True)
        selected_nodes = self._selected_nodes()
        self._connection_mode = True
        if len(selected_nodes) == 1:
            self._set_connection_source(selected_nodes[0])
            self._set_status("Select the second node to create a connection.")
        else:
            self._set_status("Select the first node, then the second node to connect.")

    def cancel_connection(self, *, silent: bool = False) -> None:
        if self._connection_source is not None:
            self._connection_source.set_connection_source(False)
        self._connection_source = None
        self._connection_mode = False
        if not silent:
            self._set_status("Connection mode cancelled.")

    def on_node_activated(self, node: Node) -> None:
        """Create a persisted edge only when explicit connection mode is active."""
        if not self._connection_mode:
            return
        if self._connection_source is None:
            self._set_connection_source(node)
            self.scene.clearSelection()
            node.setSelected(True)
            self._set_status("Select the second node to create a connection.")
            return
        if self._connection_source is node:
            self.cancel_connection()
            return

        source = self._connection_source
        self.cancel_connection(silent=True)
        self.add_edge(source, node)

    def add_edge(self, source: Node, target: Node) -> Edge | None:
        """Persist and render a relation after rejecting self-links and duplicates."""
        case_id = self._require_case()
        if case_id is None:
            return None
        if source is target:
            self._set_status("A node cannot be connected to itself.")
            return None
        if any(edge.connects(source, target) for edge in self._edges.values()):
            self._set_status("These nodes are already connected.")
            return None

        try:
            record = self.repository.create_edge(case_id, source.id, target.id)
        except Exception as error:
            self._show_error("Could not create connection", error)
            return None

        existing = self._edges.get(record.id)
        if existing is not None:
            return existing
        edge = self._add_edge_to_scene(record.id, source, target)
        self.apply_filters()
        self._set_status("Connection saved.")
        self.board_changed.emit()
        return edge

    def edit_selected_node(self) -> None:
        """Edit the data of exactly one selected node, if any."""
        selected_nodes = self._selected_nodes()
        if len(selected_nodes) != 1:
            self._set_status("Select exactly one node to edit.")
            return
        self.edit_node(selected_nodes[0])

    def edit_node(self, node: Node) -> None:
        """Edit the data of a specific node, if it belongs to the current case."""
        case_id = self._require_case()
        if case_id is None:
            return
        dialog = NodeEditorDialog(
            self,
            attachments_dir=self._attachments_dir,
            initial=node.data,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self.repository.update_node(case_id, node.id, dialog.draft())
        except Exception as error:
            self._show_error("Could not update board node", error)
            return
        node.set_data(updated)
        self.apply_filters()
        self._set_status("Node saved.")
        self.board_changed.emit()

    def delete_selected_items(self) -> None:
        """Delete all selected nodes and edges after confirmation, if any."""
        case_id = self._require_case()
        if case_id is None:
            return
        selected_nodes = self._selected_nodes()
        selected_edges = self._selected_edges()
        if not selected_nodes and not selected_edges:
            self._set_status("Select nodes or connections to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Delete selected board data",
            f"Delete {len(selected_nodes)} node(s) and {len(selected_edges)}"
            + "selected connection(s)?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            for node in tuple(selected_nodes):
                self.repository.delete_node(case_id, node.id)
                self._remove_node_from_scene(node)
            for edge in tuple(selected_edges):
                if edge.id in self._edges:
                    self.repository.delete_edge(case_id, edge.id)
                    self._remove_edge_from_scene(edge)
        except Exception as error:
            self._show_error("Could not delete selected board data", error)
            self.load_case(case_id, self.current_case_name or "Current case")
            return

        self._clear_analysis_highlight()
        self._set_status("Selected board data deleted.")
        self.board_changed.emit()

    def clear_board(self) -> None:
        """Delete all nodes and edges from the current case after confirmation."""
        case_id = self._require_case()
        if case_id is None:
            return
        if not self._nodes:
            self._set_status("This case board is already empty.")
            return
        reply = QMessageBox.question(
            self,
            "Clear case board",
            f'Delete every node and connection from "{self.current_case_name}"?',
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.repository.clear_case_board(case_id)
        except Exception as error:
            self._show_error("Could not clear case board", error)
            return
        self._clear_scene_items()
        self._set_status("Case board cleared.")
        self.board_changed.emit()

    def find_shortest_path(self) -> None:
        """Highlight the shortest graph path between two selected Person nodes."""
        case_id = self._require_case()
        if case_id is None:
            return
        selected = self._selected_nodes()
        if len(selected) != 2 or any(
            node.node_type != BoardNodeType.PERSON for node in selected
        ):
            self._set_status("Select exactly two Person nodes, then run shortest path.")
            return
        try:
            result = self.repository.shortest_path(
                case_id,
                selected[0].id,
                selected[1].id,
            )
        except Exception as error:
            self._show_error("Could not calculate shortest path", error)
            return
        if result is None:
            self._clear_analysis_highlight()
            self._set_status("No connection path exists between the selected people.")
            return

        node_ids, edge_ids = result
        self._set_analysis_highlight(set(node_ids), set(edge_ids))
        self._set_status(f"Shortest path highlighted: {len(edge_ids)} connection(s).")

    def find_most_indirectly_connected_person(self) -> None:
        """
        Find the person with the largest number of nodes at graph distance >= 2.
        So calculates which person is most indirectly connected to other
        nodes in the case board.
        Indirectly means >= 2 edges away, so not directly connected.
        """
        case_id = self._require_case()
        if case_id is None:
            return

        people = [
            node
            for node in self._nodes.values()
            if node.node_type == BoardNodeType.PERSON
        ]
        if not people:
            self._set_status("This case has no Person nodes.")
            return

        adjacency: dict[str, set[str]] = {node_id: set() for node_id in self._nodes}
        for edge in self._edges.values():
            adjacency[edge.source.id].add(edge.target.id)
            adjacency[edge.target.id].add(edge.source.id)

        best_node: Node | None = None
        best_score = -1
        best_reachable = 0
        for person in people:
            distances = self._shortest_distances(person.id, adjacency)
            indirect_count = sum(1 for distance in distances.values() if distance >= 2)
            reachable_count = len(distances) - 1
            if indirect_count > best_score:
                best_node = person
                best_score = indirect_count
                best_reachable = reachable_count

        assert best_node is not None
        self.scene.clearSelection()
        best_node.setSelected(True)
        self._set_analysis_highlight({best_node.id}, set())
        self._set_status(
            f'Most indirectly connected person: "{best_node.title}" '
            f"({best_score} node(s) at distance >= 2; {best_reachable}"
            + " reachable in total)."
        )

    def open_context_menu(self, position: QPoint) -> None:
        """
        Open a right-click context menu with actions relevant to
        the clicked item or empty space.
        """
        item = self._normalise_graphics_item(self.view.itemAt(position))
        menu = QMenu(self)
        if isinstance(item, Node):
            self.scene.clearSelection()
            item.setSelected(True)
            menu.addAction("Edit node", lambda: self.edit_node(item))
            menu.addAction("Connect from this node", lambda: self._connect_from(item))
            if item.attachments:
                menu.addAction(
                    "Open file or link...", lambda: self.open_attachment(item)
                )
            menu.addSeparator()
            menu.addAction("Delete node", lambda: self.delete_node_from_menu(item))
        elif isinstance(item, Edge):
            self.scene.clearSelection()
            item.setSelected(True)
            menu.addAction(
                "Delete connection", lambda: self.delete_edge_from_menu(item)
            )
        else:
            menu.addAction("Add node", self.add_node_dialog)
            menu.addAction("Fit board", self.fit_board)
        menu.exec(self.view.viewport().mapToGlobal(position))

    def open_attachment(self, node: Node) -> None:
        """Open a local file or URL from the node's attachments."""
        choices = list(node.attachments)

        if not choices:
            self._set_status("This node has no files or links.")
            return

        if len(choices) == 1:
            selected = choices[0]
        else:

            selected, accepted = QInputDialog.getItem(
                self,
                "Open file or link",
                "Choose reference:",
                choices,
                0,
                False,
            )
            if not accepted:
                return

        parsed_url = QUrl(selected)

        if parsed_url.scheme() in {"http", "https"}:
            url = parsed_url
        else:
            if parsed_url.isLocalFile():
                path = Path(parsed_url.toLocalFile())
            else:
                path = Path(selected).expanduser()
                if not path.is_absolute():
                    path = self._base_dir / path

            if not path.is_file():
                self._set_status(f"Local file does not exist: {path}")
                return

            url = QUrl.fromLocalFile(str(path.resolve()))

        if not QDesktopServices.openUrl(url):
            self._set_status("Could not ask the system to open this file or link.")

    def fit_board(self) -> None:
        """Zoom and pan the view to fit all nodes and edges, or the default scene."""
        if self._nodes or self._edges:
            rect = self.scene.itemsBoundingRect().adjusted(-70.0, -70.0, 70.0, 70.0)
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.view.fitInView(self.SCENE_RECT, Qt.AspectRatioMode.KeepAspectRatio)

    def apply_filters(self) -> None:
        """Filter nodes and edges by type and search query."""
        selected_type = self.filter_combo.currentData()
        query = self.search_input.text().strip().casefold()

        for node in self._nodes.values():
            matches_type = (
                selected_type is None or node.node_type.value == selected_type
            )
            searchable = "\n".join(
                (
                    node.title,
                    node.description,
                    node.occurred_at or "",
                    *node.attachments,
                )
            ).casefold()
            node.setVisible(matches_type and (not query or query in searchable))

        for edge in self._edges.values():
            edge.setVisible(edge.source.isVisible() and edge.target.isVisible())

    def clear_filters(self) -> None:
        """Reset the filter combo and search input, then show all nodes and edges."""
        self.filter_combo.setCurrentIndex(0)
        self.search_input.clear()
        self.apply_filters()

    def _add_node_to_scene(self, record: BoardNode) -> Node:
        """Add a node to the scene."""
        node = Node(record)
        node.setPos(record.x, record.y)
        node.activated.connect(self.on_node_activated)
        node.edit_requested.connect(self.edit_node)
        node.position_persist_requested.connect(self.persist_node_position)
        self.scene.addItem(node)
        self._nodes[node.id] = node
        return node

    def _add_edge_to_scene(self, edge_id: str, source: Node, target: Node) -> Edge:
        """Add an edge to the scene."""
        edge = Edge(edge_id, source, target)
        self.scene.addItem(edge)
        source.add_edge(edge)
        target.add_edge(edge)
        edge.update_position()
        self._edges[edge.id] = edge
        return edge

    def persist_node_position(self, node: Node) -> None:
        """Persist the node's position in the database."""
        if not self.current_case_id or node.id not in self._nodes:
            return
        try:
            self.repository.update_node_position(
                self.current_case_id,
                node.id,
                node.pos().x(),
                node.pos().y(),
            )
        except Exception as error:
            self._set_status(f"Position was not saved: {error}")
            return
        self.board_changed.emit()

    def _remove_node_from_scene(self, node: Node) -> None:
        """Remove a node and all its edges from the scene and internal state."""
        if node.id not in self._nodes:
            return
        if node is self._connection_source:
            self.cancel_connection(silent=True)
        for edge in tuple(node.edges):
            self._remove_edge_from_scene(edge)
        self.scene.removeItem(node)
        self._nodes.pop(node.id, None)

    def _remove_edge_from_scene(self, edge: Edge) -> None:
        """Remove an edge from the scene and internal state."""
        if edge.id not in self._edges:
            return
        edge.detach()
        self.scene.removeItem(edge)
        self._edges.pop(edge.id, None)

    def _clear_scene_items(self) -> None:
        """Remove all nodes and edges from the scene and internal state."""
        self.cancel_connection(silent=True)
        for edge in tuple(self._edges.values()):
            self._remove_edge_from_scene(edge)
        for node in tuple(self._nodes.values()):
            self.scene.removeItem(node)
        self._nodes.clear()
        self._edges.clear()
        self._analysis_node_ids.clear()
        self._analysis_edge_ids.clear()

    def _connect_from(self, node: Node) -> None:
        """
        Start a connection from a specific node,
        cancelling any previous connection mode.
        """
        self.cancel_connection(silent=True)
        self._connection_mode = True
        self._set_connection_source(node)
        self._set_status("Select the second node to create a connection.")

    def _set_connection_source(self, node: Node) -> None:
        """
        Set the node that is the source of a new connection, updating its visual state.
        """
        if self._connection_source is not None:
            self._connection_source.set_connection_source(False)
        self._connection_source = node
        node.set_connection_source(True)

    def _selected_nodes(self) -> list[Node]:
        """Return a list of selected nodes in the scene."""
        return [item for item in self.scene.selectedItems() if isinstance(item, Node)]

    def _selected_edges(self) -> list[Edge]:
        """Return a list of selected edges in the scene."""
        return [item for item in self.scene.selectedItems() if isinstance(item, Edge)]

    def _next_node_position(self) -> tuple[float, float]:
        """
        Return a default position for a new node, based on the number of existing nodes.
        """
        index = len(self._nodes)
        return 100.0 + (index % 6) * 320.0, 100.0 + (index // 6) * 210.0

    def _set_analysis_highlight(self, node_ids: set[str], edge_ids: set[str]) -> None:
        """
        Highlight the specified nodes and edges for analysis,
        clearing any previous highlights.
        """
        self._clear_analysis_highlight()
        self._analysis_node_ids = node_ids
        self._analysis_edge_ids = edge_ids
        for node_id in node_ids:
            if node := self._nodes.get(node_id):
                node.set_analysis_highlight(True)
        for edge_id in edge_ids:
            if edge := self._edges.get(edge_id):
                edge.set_analysis_highlight(True)

    def _clear_analysis_highlight(self) -> None:
        """Clear any highlighted nodes and edges from previous analysis."""
        for node_id in self._analysis_node_ids:
            if node := self._nodes.get(node_id):
                node.set_analysis_highlight(False)
        for edge_id in self._analysis_edge_ids:
            if edge := self._edges.get(edge_id):
                edge.set_analysis_highlight(False)
        self._analysis_node_ids.clear()
        self._analysis_edge_ids.clear()

    def clear_analysis(self) -> None:
        """Clear any highlighted nodes and edges from previous analysis."""
        self._clear_analysis_highlight()
        self._set_status("Analysis highlights cleared.")

    @staticmethod
    def _shortest_distances(
        start: str, adjacency: dict[str, set[str]]
    ) -> dict[str, int]:
        """
        Return a mapping of node IDs to their shortest distance from the start node,
        using a breadth-first search algorithm.
        Parameters:
            start: The ID of the starting node.
            adjacency: A dictionary mapping node IDs to sets of adjacent node IDs.
            Example:
                {
                    "node1": {"node2", "node3"},
                    "node2": {"node1"},
                    "node3": {"node1"},
                }
        """
        # At the beggining only the start node is known to be at distance 0 from itself
        distances = {start: 0}
        # List of nodes to visit, starting with the start node
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbour in adjacency.get(current, set()):
                if neighbour not in distances:
                    distances[neighbour] = distances[current] + 1
                    queue.append(neighbour)
        return distances

    def delete_node_from_menu(self, node: Node) -> None:
        """Delete a node from the context menu, after selecting it."""
        self.scene.clearSelection()
        node.setSelected(True)
        self.delete_selected_items()

    def delete_edge_from_menu(self, edge: Edge) -> None:
        """Delete an edge from the context menu, after selecting it."""
        self.scene.clearSelection()
        edge.setSelected(True)
        self.delete_selected_items()

    def _require_case(self) -> str | None:
        """Return the currently loaded case ID, or None if no case is loaded."""
        if self.current_case_id is None:
            self._set_status("Select a case in Cases before editing a board.")
            return None
        return self.current_case_id

    def _set_case_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable all controls that require a loaded case."""
        for widget in self._case_required_widgets:
            widget.setEnabled(enabled)

    def _create_shortcuts(self) -> None:
        """Create keyboard shortcuts for common board actions."""
        shortcuts: list[tuple[str, QKeySequence, Callable[[], None]]] = [
            (
                "Add node",
                QKeySequence(QKeySequence.StandardKey.New),
                self.add_node_dialog,
            ),
            (
                "Edit selected",
                QKeySequence(QKeySequence.StandardKey.Open),
                self.edit_selected_node,
            ),
            (
                "Delete selected",
                QKeySequence(QKeySequence.StandardKey.Delete),
                self.delete_selected_items,
            ),
            (
                "Cancel connection",
                QKeySequence(QKeySequence(Qt.Key.Key_Escape)),
                self.cancel_connection,
            ),
            (
                "Focus search",
                QKeySequence(QKeySequence.StandardKey.Find),
                self.search_input.setFocus,
            ),
            ("Zoom in", QKeySequence(QKeySequence("Ctrl++")), self.view.zoom_in),
            ("Zoom out", QKeySequence(QKeySequence("Ctrl+-")), self.view.zoom_out),
        ]
        for text, shortcut, handler in shortcuts:
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.triggered.connect(handler)
            self.addAction(action)

    @staticmethod
    def _normalise_graphics_item(item: QGraphicsItem | None) -> QGraphicsItem | None:
        """Normalise a graphics item to its base type."""
        current = item
        while current is not None and not isinstance(current, (Node, Edge)):
            current = current.parentItem()
        return current

    def _show_error(self, title: str, error: Exception) -> None:
        """Show an error message box and update the status label."""
        QMessageBox.critical(self, title, str(error))
        self._set_status(f"{title}: {error}")

    def _set_status(self, text: str) -> None:
        """Update the status label with a message."""
        self.status_label.setText(text)
