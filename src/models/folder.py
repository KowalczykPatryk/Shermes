"""
Contains dataclass representing folder in which cases are stored.
"""

from dataclasses import dataclass


@dataclass
class Folder:
    id: str  # elementId()
    name: str
    # flag indicating whether folder is system folder (e.g. "All Cases") or user-created
    system: bool = False
