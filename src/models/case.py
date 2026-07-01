"""
Represents a criminal case stored inside a folder.
It is used in the case repository.
"""

from dataclasses import dataclass


@dataclass
class Case:
    """
    Represents a criminal case stored inside a folder.
    It is used in the case repository.
    """

    id: str
    name: str
