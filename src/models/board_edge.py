"""Model for a relationship on an investigation board."""

from __future__ import annotations

from dataclasses import dataclass


# frozen=True makes the dataclass immutable, which is
# useful for hashability and equality checks
# slots=True makes the dataclass more memory efficient by
# preventing the creation of a __dict__ for each instance
@dataclass(frozen=True, slots=True)
class BoardEdge:
    """
    An undirected semantic relationship between two nodes of one case.
    """

    id: str
    case_id: str
    source_id: str
    target_id: str
