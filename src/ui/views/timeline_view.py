"""Chronological case timeline derived from persisted board data."""

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.database.neo4j_client import Neo4jClient
from src.models.board_node import BoardNode
from src.repositories.board_repository import BoardRepository


class TimelineMarker(QWidget):
    """Circular marker placed on the horizontal timeline axis."""

    SIZE = 18

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt API name
        """Draw a red marker with a light outline."""
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        painter.setPen(QPen(QColor("#f0d3af"), 3.0))
        painter.setBrush(QColor("#b83a30"))

        painter.drawEllipse(
            2,
            2,
            self.width() - 4,
            self.height() - 4,
        )


class TimelineEntryWidget(QWidget):
    """One dated node displayed as a marker and information card on a timeline."""

    CARD_WIDTH = 280
    WHEN_HEIGHT = 48
    MARKER_SIZE = 18
    CARD_TOP_GAP = 14

    TRACK_Y = WHEN_HEIGHT + MARKER_SIZE // 2

    def __init__(self, node: BoardNode, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setStyleSheet("background-color: transparent; border: none;")

        self.setFixedWidth(self.CARD_WIDTH)

        self.when_label = QLabel(self._format_when(node.occurred_at or ""))
        self.when_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
        )
        self.when_label.setWordWrap(True)
        self.when_label.setFixedHeight(self.WHEN_HEIGHT)

        self.marker = TimelineMarker()

        marker_holder = QWidget()
        marker_holder.setStyleSheet("background-color: transparent; border: none;")
        marker_holder.setAutoFillBackground(False)

        marker_layout = QHBoxLayout(marker_holder)
        marker_layout.setContentsMargins(0, 0, 0, 0)
        marker_layout.setSpacing(0)

        marker_layout.addWidget(
            self.marker,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )

        marker_holder.setFixedHeight(self.MARKER_SIZE)

        self.card_label = QLabel(self._card_html(node))
        self.card_label.setTextFormat(Qt.TextFormat.RichText)
        self.card_label.setWordWrap(True)
        self.card_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.when_label)
        layout.addWidget(marker_holder)
        layout.addSpacing(self.CARD_TOP_GAP)
        layout.addWidget(self.card_label)

    @staticmethod
    def _format_when(timestamp: str) -> str:
        """Make an ISO timestamp easier to read while keeping all information."""
        return timestamp.replace("T", "\n", 1)

    @staticmethod
    def _card_html(node: BoardNode) -> str:
        """Build a card containing all user-facing data stored on one node."""
        node_type = escape(node.node_type.value.replace("_", " ").title())
        title = escape(node.title)
        occurred_at = escape(node.occurred_at or "")

        if node.description.strip():
            description = escape(node.description).replace("\n", "<br/>")
        else:
            description = "<i>No description</i>"

        if node.attachments:
            attachments = "<br/>".join(
                f"&bull; {escape(attachment)}" for attachment in node.attachments
            )
        else:
            attachments = "<i>No attachments</i>"

        return (
            f"<b>{title}</b><br/>"
            f"<b>Type:</b> {node_type}<br/>"
            f"<b>When:</b> {occurred_at}<br/><br/>"
            f"<b>Description:</b><br/>{description}<br/><br/>"
            f"<b>Attachments:</b><br/>{attachments}"
        )


class TimelineLane(QWidget):
    """Horizontal timeline track that draws one line behind entry markers."""

    SIDE_MARGIN = 40
    ENTRY_SPACING = 28
    MINIMUM_HEIGHT = 170

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(
            self.SIDE_MARGIN,
            0,
            self.SIDE_MARGIN,
            0,
        )
        self._layout.setSpacing(self.ENTRY_SPACING)

        self.setFixedSize(1, self.MINIMUM_HEIGHT)

    def set_nodes(self, nodes: list[BoardNode]) -> None:
        """Replace the visible timeline entries with sorted dated nodes."""
        self._clear_entries()

        if not nodes:
            self.setFixedSize(1, self.MINIMUM_HEIGHT)
            self.update()
            return

        for node in nodes:
            entry = TimelineEntryWidget(node)
            self._layout.addWidget(
                entry,
                alignment=Qt.AlignmentFlag.AlignTop,
            )

        entry_count = len(nodes)
        width = (
            2 * self.SIDE_MARGIN
            + entry_count * TimelineEntryWidget.CARD_WIDTH
            + max(0, entry_count - 1) * self.ENTRY_SPACING
        )

        self._layout.activate()

        height = max(
            self.MINIMUM_HEIGHT,
            self._layout.sizeHint().height(),
        )

        self.setFixedSize(width, height)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 - Qt API name
        """Draw the horizontal time axis behind all timeline markers."""
        super().paintEvent(event)

        if self._layout.count() == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#a93a31"), 2.5))

        track_y = TimelineEntryWidget.TRACK_Y

        painter.drawLine(
            self.SIDE_MARGIN // 2,
            track_y,
            self.width() - self.SIDE_MARGIN // 2,
            track_y,
        )

    def _clear_entries(self) -> None:
        """Remove and schedule deletion of all existing timeline widgets."""
        while self._layout.count():
            item = self._layout.takeAt(0)

            if widget := item.widget():
                widget.deleteLater()


class TimelineView(QWidget):
    """Horizontal timeline containing every node that has a date and time."""

    def __init__(self, BASE_DIR: Path) -> None:
        super().__init__()
        del BASE_DIR

        self.repository = BoardRepository(Neo4jClient())
        self.current_case_id: str | None = None
        self.current_case_name: str | None = None

        self.case_label = QLabel("Timeline: no case selected")
        self.case_label.setStyleSheet("font-weight: bold; font-size: 16px;")

        self.empty_label = QLabel("Select a case to view its dated nodes.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)

        self.timeline_lane = TimelineLane()

        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidget(self.timeline_lane)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.timeline_scroll.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.timeline_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.timeline_scroll.hide()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self.case_label)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.timeline_scroll, 1)

    def load_case(self, case_id: str, case_name: str) -> None:
        """Load and display the dated nodes of one case."""
        self.current_case_id = case_id
        self.current_case_name = case_name
        self.case_label.setText(f"Timeline: {case_name}")
        self.refresh()

    def unload_case(self) -> None:
        """Clear timeline data after the active case is removed or closed."""
        self.current_case_id = None
        self.current_case_name = None

        self.case_label.setText("Timeline: no case selected")
        self.empty_label.setText("Select a case to view its dated nodes.")
        self.empty_label.show()

        self.timeline_lane.set_nodes([])
        self.timeline_scroll.hide()

    def rename_current_case(self, case_id: str, name: str) -> None:
        """Keep the visible timeline title synchronised with a renamed case."""
        if case_id == self.current_case_id:
            self.current_case_name = name
            self.case_label.setText(f"Timeline: {name}")

    def refresh(self) -> None:
        """Load, sort and render every node with an enabled timestamp."""
        if self.current_case_id is None:
            return

        try:
            nodes = self.repository.get_nodes(self.current_case_id)
        except Exception as error:
            self.timeline_lane.set_nodes([])
            self.timeline_scroll.hide()

            self.empty_label.setText(f"Timeline could not load: {error}")
            self.empty_label.show()
            return

        dated_nodes = sorted(
            (node for node in nodes if node.occurred_at),
            key=lambda node: node.occurred_at or "",
        )

        if not dated_nodes:
            self.timeline_lane.set_nodes([])
            self.timeline_scroll.hide()

            self.empty_label.setText(
                f'Timeline: "{self.current_case_name}" has no nodes '
                "with a date and time."
            )
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.timeline_scroll.show()
        self.timeline_lane.set_nodes(dated_nodes)
