"""Typed, movable image-based graphics node used by the case board."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPixmapItem,
    QGraphicsSceneMouseEvent,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from src.models.board_node import BoardNode, BoardNodeType

if TYPE_CHECKING:
    from src.ui.graphic_items.edge import Edge


@dataclass(frozen=True, slots=True)
class TextOffset:
    """Additional text displacement for one node background."""

    x: float = 0.0
    y: float = 0.0


class Node(QGraphicsObject):
    """A movable investigation node rendered from a type-specific PNG card."""

    activated = Signal(object)
    edit_requested = Signal(object)
    position_persist_requested = Signal(object)

    ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets" / "nodes"

    WIDTH = 270.0  # Width of the node card, including padding
    MINIMUM_BODY_HEIGHT = 120.0  # Minimum height of the node, excluding the pin
    PADDING = 12.0  # Padding around the text inside the node card

    PIN_SIZE = 44.0  # Size of the pin image
    PIN_OVERLAP = 60.0  # Amount of the pin that overlaps the top of the node card

    PIN_Y_OFFSET = 3.0  # Moves the pin and image down to make room

    PIN_ABOVE_CARD = PIN_Y_OFFSET + PIN_SIZE - PIN_OVERLAP

    EDGE_INSET = 40.0  # Inset from the node card edges where edges can attach
    EDGE_TOP_OFFSET = (
        70.0  # Offset from the top of the node card where edges can attach
    )

    TYPE_LABELS: dict[BoardNodeType, str] = {
        BoardNodeType.PHOTO: "PHOTO",
        BoardNodeType.NOTE: "NOTE",
        BoardNodeType.PERSON: "PERSON",
        BoardNodeType.EVENT: "EVENT",
        BoardNodeType.PLACE: "PLACE",
        BoardNodeType.TIMESTAMP: "TIMESTAMP",
        BoardNodeType.LINK: "LINK",
        BoardNodeType.PDF: "PDF",
    }

    TYPE_IMAGE_FILES: dict[BoardNodeType, str] = {
        BoardNodeType.PHOTO: "photo.png",
        BoardNodeType.NOTE: "note.png",
        BoardNodeType.PERSON: "person.png",
        BoardNodeType.EVENT: "event.png",
        BoardNodeType.PLACE: "place.png",
        BoardNodeType.TIMESTAMP: "timestamp.png",
        BoardNodeType.LINK: "link.png",
        BoardNodeType.PDF: "pdf.png",
    }

    PIN_IMAGE_FILES: tuple[str, ...] = (
        "pin1.png",
        "pin2.png",
        "pin3.png",
        "pin4.png",
        "pin5.png",
        "pin6.png",
        "pin7.png",
        "pin8.png",
    )

    TEXT_OFFSETS: dict[BoardNodeType, TextOffset] = {
        BoardNodeType.PHOTO: TextOffset(x=30.0, y=40.0),
        BoardNodeType.NOTE: TextOffset(x=50.0, y=8.0),
        BoardNodeType.PERSON: TextOffset(x=10.0, y=120.0),
        BoardNodeType.EVENT: TextOffset(x=80.0, y=20.0),
        BoardNodeType.PLACE: TextOffset(x=40.0, y=20.0),
        BoardNodeType.TIMESTAMP: TextOffset(x=0.0, y=-60.0),
        BoardNodeType.LINK: TextOffset(x=10.0, y=-20.0),
        BoardNodeType.PDF: TextOffset(x=0.0, y=8.0),
    }

    PHOTO_PREVIEW_RECT = QRectF(
        45.0,  # x: distance from the left edge of the node
        35.0,  # y: distance from the top edge of the node
        185.0,  # max width of the preview
        145.0,  # max height of the preview
    )

    PHOTO_EXTENSIONS = frozenset(
        {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
        }
    )

    def __init__(
        self,
        data: BoardNode,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self._data = data
        self._rect = QRectF(
            0.0,
            0.0,
            self.WIDTH,
            self.PIN_ABOVE_CARD + self.MINIMUM_BODY_HEIGHT,
        )
        self._body_rect = QRectF(
            0.0,
            self.PIN_ABOVE_CARD,
            self.WIDTH,
            self.MINIMUM_BODY_HEIGHT,
        )

        self._edges: set[Edge] = set()
        self._connection_source = False
        self._analysis_highlight = False
        self._pressed_position = None

        self._background_item = QGraphicsPixmapItem(self)
        self._background_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._background_item.setZValue(0.0)

        self._photo_preview_item = QGraphicsPixmapItem(self)
        self._photo_preview_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._photo_preview_item.setZValue(1.0)
        self._photo_preview_item.setVisible(False)

        self._text_item = QGraphicsTextItem(self)
        self._text_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._text_item.setDefaultTextColor(QColor("#000000"))
        self._text_item.setZValue(1.0)

        self._pin_item = QGraphicsPixmapItem(self)
        self._pin_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._pin_item.setZValue(2.0)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(1.0)

        self._refresh_presentation()

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def node_type(self) -> BoardNodeType:
        return self._data.node_type

    @property
    def title(self) -> str:
        return self._data.title

    @property
    def description(self) -> str:
        return self._data.description

    @property
    def attachments(self) -> tuple[str, ...]:
        return self._data.attachments

    @property
    def occurred_at(self) -> str | None:
        return self._data.occurred_at

    @property
    def data(self) -> BoardNode:
        return self._data

    @property
    def edges(self) -> tuple[Edge, ...]:
        """Return a stable snapshot of incident edges."""
        return tuple(self._edges)

    def boundingRect(self) -> QRectF:  # noqa: N802 - Qt API name
        """Return the complete area occupied by the pin, card and outline."""
        return self._rect.adjusted(-4.0, -4.0, 4.0, 4.0)

    def connection_rect(self) -> QRectF:
        """Return an inset card area used as the edge attachment boundary."""
        attachment_rect = self._body_rect.adjusted(
            self.EDGE_INSET,
            self.EDGE_TOP_OFFSET,
            -self.EDGE_INSET,
            -self.EDGE_INSET,
        )
        return self.mapRectToScene(attachment_rect)

    def _pin_filename(self) -> str:
        """Return one stable decorative pin filename for this node."""
        digest = hashlib.blake2b(
            self.id.encode("utf-8"),
            digest_size=8,
        ).digest()

        pin_index = int.from_bytes(digest, "big") % len(self.PIN_IMAGE_FILES)

        return self.PIN_IMAGE_FILES[pin_index]

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Draw a state-specific outline around the PNG card."""
        del option, widget

        if self._connection_source:
            outline = QColor("#f2bf3b")
            width = 3.5
        elif self._analysis_highlight:
            outline = QColor("#3c88c8")
            width = 3.5
        elif self.isSelected():
            outline = QColor("#c27125")
            width = 2.8
        else:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(outline, width))

        painter.drawRoundedRect(
            self._body_rect.adjusted(-2.5, -2.5, 2.5, 2.5),
            12.0,
            12.0,
        )

    def set_data(self, data: BoardNode) -> None:
        """Apply persisted data after an edit and refresh the visual card."""
        if data.id != self.id:
            raise ValueError("Cannot replace a node with a different identifier.")

        self._data = data
        self._refresh_presentation()

    def set_connection_source(self, enabled: bool) -> None:
        """Highlight this node as the first selected connection endpoint."""
        if self._connection_source != enabled:
            self._connection_source = enabled
            self.update()

    def set_analysis_highlight(self, enabled: bool) -> None:
        """Highlight this node as part of a graph-analysis result."""
        if self._analysis_highlight != enabled:
            self._analysis_highlight = enabled
            self.update()

    def add_edge(self, edge: Edge) -> None:
        """Register an edge connected to this node."""
        self._edges.add(edge)

    def remove_edge(self, edge: Edge) -> None:
        """Remove an edge from this node's incident-edge collection."""
        self._edges.discard(edge)

    def mousePressEvent(
        self,
        event: QGraphicsSceneMouseEvent,
    ) -> None:  # noqa: N802 - Qt API name
        """Store the original position and activate the node on left click."""
        self._pressed_position = self.pos()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self)

    def mouseReleaseEvent(
        self,
        event: QGraphicsSceneMouseEvent,
    ) -> None:  # noqa: N802 - Qt API name
        """Persist the node position when it was moved."""
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        if self._pressed_position is not None and self.pos() != self._pressed_position:
            self.position_persist_requested.emit(self)

        self._pressed_position = None

    def mouseDoubleClickEvent(
        self,
        event: QGraphicsSceneMouseEvent,
    ) -> None:  # noqa: N802 - Qt API name
        """Request node editing after a left-button double click."""
        super().mouseDoubleClickEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            self.edit_requested.emit(self)

    def itemChange(
        self,
        change: QGraphicsItem.GraphicsItemChange,
        value: Any,
    ) -> Any:  # noqa: N802 - Qt API name
        """Update connected edges and outline when relevant item state changes."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._update_incident_edges()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()

        return super().itemChange(change, value)

    def _refresh_presentation(self) -> None:
        """Refresh node geometry, background, optional photo preview, pin and text."""
        offset = self.TEXT_OFFSETS[self.node_type]

        text_left = self.PADDING + offset.x
        text_top = self.PIN_ABOVE_CARD + self.PIN_OVERLAP + self.PADDING + offset.y

        self._text_item.setHtml(self._text_html())
        self._text_item.setTextWidth(self.WIDTH - text_left - self.PADDING)

        text_height = self._text_item.document().size().height()

        source_preview = self._photo_preview_source()

        scaled_preview = (
            self._scaled_photo_preview(source_preview)
            if source_preview is not None
            else None
        )

        text_bottom = text_top + text_height + self.PADDING

        preview_bottom = 0.0
        if scaled_preview is not None:
            preview_bottom = self.PHOTO_PREVIEW_RECT.bottom() + self.PADDING

        minimum_bottom = self.PIN_ABOVE_CARD + self.MINIMUM_BODY_HEIGHT

        node_bottom = max(
            minimum_bottom,
            text_bottom,
            preview_bottom,
        )

        body_height = node_bottom - self.PIN_ABOVE_CARD

        self.prepareGeometryChange()

        self._body_rect = QRectF(
            0.0,
            self.PIN_ABOVE_CARD,
            self.WIDTH,
            body_height,
        )

        self._rect = QRectF(
            0.0,
            0.0,
            self.WIDTH,
            self.PIN_ABOVE_CARD + body_height,
        )

        self._text_item.setPos(
            text_left,
            text_top,
        )

        self._update_background_pixmap()
        self._update_photo_preview(scaled_preview)
        self._update_pin_pixmap()

        self._update_incident_edges()
        self.update()

    def _update_background_pixmap(self) -> None:
        """Scale the node image without changing its proportions."""
        filename = self.TYPE_IMAGE_FILES[self.node_type]
        source = self._load_pixmap(filename)

        scaled = source.scaledToWidth(
            int(self.WIDTH),
            Qt.TransformationMode.SmoothTransformation,
        )

        self._background_item.setPixmap(scaled)
        self._background_item.setPos(
            self._body_rect.left(),
            self._body_rect.top(),
        )

    def _update_pin_pixmap(self) -> None:
        """Scale and centre the pin PNG above the card."""
        source = self._load_pixmap(self._pin_filename())

        scaled = source.scaled(
            QSize(int(self.PIN_SIZE), int(self.PIN_SIZE)),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._pin_item.setPixmap(scaled)
        self._pin_item.setZValue(10.0)

        self._pin_item.setPos(
            (self.WIDTH - scaled.width()) / 2.0,
            self.PIN_Y_OFFSET,
        )

    def _load_pixmap(self, filename: str) -> QPixmap:
        """Load one asset and raise a clear error when it is unavailable."""
        path = self.ASSETS_DIR / filename
        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            raise FileNotFoundError(f"Could not load node image: {path}")

        return pixmap

    def _text_html(self) -> str:
        """Build the rich text placed on top of the node PNG."""
        type_label = self.TYPE_LABELS[self.node_type]
        title = escape(self.title)
        description = escape(self.description.strip()).replace("\n", "<br/>")

        type_label_size = 8
        if self.node_type == BoardNodeType.PERSON:
            type_label_size = 16
        elif self.node_type == BoardNodeType.LINK:
            type_label_size = 12
        elif self.node_type == BoardNodeType.NOTE:
            type_label_size = 16
        elif self.node_type == BoardNodeType.TIMESTAMP:
            type_label_size = 16
        elif self.node_type == BoardNodeType.PLACE:
            type_label_size = 24
        elif self.node_type == BoardNodeType.EVENT:
            type_label_size = 12

        title_size = 8
        if self.node_type == BoardNodeType.PERSON:
            title_size = 16
        elif self.node_type == BoardNodeType.LINK:
            title_size = 12
        elif self.node_type == BoardNodeType.NOTE:
            title_size = 16
        elif self.node_type == BoardNodeType.TIMESTAMP:
            title_size = 20
        elif self.node_type == BoardNodeType.PLACE:
            title_size = 24
        elif self.node_type == BoardNodeType.EVENT:
            title_size = 16

        background_color = "transparent"
        if self.node_type == BoardNodeType.PLACE:
            background_color = "rgba(255, 255, 255, 200)"
        elif self.node_type == BoardNodeType.TIMESTAMP:
            background_color = "rgba(255, 255, 255, 190)"
        elif self.node_type == BoardNodeType.PHOTO:
            background_color = "rgba(255, 255, 255, 200)"

        lines = [
            (
                f"<span style='font-size:{type_label_size}pt; color:#6c4030;"
                f"background-color:{background_color};'>"
                f"<b>{type_label}</b>"
                "</span>"
            ),
            f"<span style='font-size:{title_size}pt; color:#000000;"
            f"background-color:{background_color};'>"
            f"<b>{title}</b>"
            "</span>",
        ]

        description_size = 8
        if self.node_type == BoardNodeType.PERSON:
            description_size = 12
        elif self.node_type == BoardNodeType.LINK:
            description_size = 10
        elif self.node_type == BoardNodeType.NOTE:
            description_size = 12

        if description:
            short_description = description
            if len(short_description) > 220:
                short_description = f"{short_description[:217]}..."
            description_html = (
                f"<span style='font-size:{description_size}pt; color:#000000;"
                f"background-color:{background_color};'>"
                f"{short_description}"
                "</span>"
            )
            lines.append(description_html)

        if self.occurred_at:
            lines.append(
                f"<span style='color:#5f463a; background-color:{background_color};'>"
                f"When: {escape(self.occurred_at)}"
                "</span>"
            )

        if self.attachments:
            noun = "attachment" if len(self.attachments) == 1 else "attachments"
            lines.append(
                f"<span style='color:#5f463a; background-color:{background_color};'>"
                f"{len(self.attachments)} {noun}"
                "</span>"
            )

        return "<br/>".join(lines)

    def _update_incident_edges(self) -> None:
        """Recalculate all edge endpoints after a geometry or position change."""
        for edge in tuple(self._edges):
            edge.update_position()

    def _photo_preview_source(self) -> QPixmap | None:
        """Return the first valid local image attached to a Photo node."""
        if self.node_type != BoardNodeType.PHOTO:
            return None

        for attachment in self.attachments:
            path = Path(attachment).expanduser()

            if path.suffix.lower() not in self.PHOTO_EXTENSIONS:
                continue

            if not path.is_file():
                continue

            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap

        return None

    def _scaled_photo_preview(self, source: QPixmap) -> QPixmap:
        """Scale the photo to fit the configured preview area."""
        return source.scaled(
            self.PHOTO_PREVIEW_RECT.size().toSize(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _update_photo_preview(self, preview: QPixmap | None) -> None:
        """Place a photo preview inside the configured card area."""
        if preview is None:
            self._photo_preview_item.setVisible(False)
            return

        preview_rect = self.PHOTO_PREVIEW_RECT

        self._photo_preview_item.setPixmap(preview)
        self._photo_preview_item.setPos(
            preview_rect.x() + (preview_rect.width() - preview.width()) / 2.0,
            preview_rect.y() + (preview_rect.height() - preview.height()) / 2.0,
        )
        self._photo_preview_item.setVisible(True)
