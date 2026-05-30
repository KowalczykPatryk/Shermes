"""
Contains dataclass representing case.
"""

from dataclasses import dataclass


@dataclass
class Case:
    id: str  # elementId()
    name: str
