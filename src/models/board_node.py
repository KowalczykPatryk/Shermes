"""Models for nodes displayed on a case investigation board."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BoardNodeType(StrEnum):
    """Supported investigation-board node categories."""

    PHOTO = "photo"
    NOTE = "note"
    PERSON = "person"
    EVENT = "event"
    PLACE = "place"
    TIMESTAMP = "timestamp"
    LINK = "link"
    PDF = "pdf"


@dataclass(frozen=True, slots=True)
class BoardNode:
    """Node belonging to exactly one ``Case``."""

    id: str
    case_id: str
    node_type: BoardNodeType
    title: str
    description: str = ""
    attachments: tuple[str, ...] = field(default_factory=tuple)
    occurred_at: str | None = None
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True, slots=True)
class BoardNodeDraft:
    """Validated editable payload used when creating or updating a node."""

    node_type: BoardNodeType
    title: str
    description: str = ""
    attachments: tuple[str, ...] = field(default_factory=tuple)
    occurred_at: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("Board node title cannot be empty.")
