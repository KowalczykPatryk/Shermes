"""Selectable, persistable edge connecting two typed board nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem

if TYPE_CHECKING:
    from src.ui.graphic_items.node import Node


class Edge(QGraphicsLineItem):
    """A visual counterpart of one ``RELATED_TO`` relationship in Neo4j."""

    def __init__(self, edge_id: str, source: Node, target: Node) -> None:
        super().__init__()
        if source is target:
            raise ValueError("An edge must connect two different nodes.")

        self.id = edge_id
        self.source = source
        self.target = target
        self._analysis_highlight = False

        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(0.0)
        self._apply_pen()
        self.update_position()

    def connects(self, first: Node, second: Node) -> bool:
        return (self.source is first and self.target is second) or (
            self.source is second and self.target is first
        )

    def involves(self, node: Node) -> bool:
        return self.source is node or self.target is node

    def set_analysis_highlight(self, enabled: bool) -> None:
        if self._analysis_highlight != enabled:
            self._analysis_highlight = enabled
            self._apply_pen()

    def detach(self) -> None:
        self.source.remove_edge(self)
        self.target.remove_edge(self)

    def update_position(self) -> None:
        source_rect = self.source.connection_rect()
        target_rect = self.target.connection_rect()
        source_center = source_rect.center()
        target_center = target_rect.center()
        start = self._edge_point(source_rect, source_center, target_center)
        end = self._edge_point(target_rect, target_center, source_center)
        self.setLine(start.x(), start.y(), end.x(), end.y())

    def itemChange(self, change, value):  # noqa: N802 - Qt API name
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._apply_pen()
        return super().itemChange(change, value)

    def _apply_pen(self) -> None:
        if self._analysis_highlight:
            color = QColor("#0037EC")
            width = 5.5
        elif self.isSelected():
            color = QColor("#FF3131")
            width = 5.5
        else:
            color = QColor("#D2042D")
            width = 5.0
        self.setPen(
            QPen(
                color,
                width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin,
            )
        )

    @staticmethod
    def _edge_point(rect, center: QPointF, target: QPointF) -> QPointF:
        dx = target.x() - center.x()
        dy = target.y() - center.y()
        if dx == 0.0 and dy == 0.0:
            return center

        candidates: list[float] = []
        if dx:
            candidates.append(rect.width() / 2.0 / abs(dx))
        if dy:
            candidates.append(rect.height() / 2.0 / abs(dy))
        scale = min(candidates)
        return QPointF(center.x() + dx * scale, center.y() + dy * scale)
