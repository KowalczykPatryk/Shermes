"""
Represents a folder that can contain subfolders and cases.
It is used in the folder repository.
"""

from dataclasses import dataclass


@dataclass
class Folder:
    """
    Represents a folder that can contain subfolders and cases.
    It is used in the folder repository.
    """

    id: str
    name: str
    system: bool = False
