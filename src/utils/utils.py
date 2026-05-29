"""
Contains utility functions for the application.
"""


def load_stylesheet(path: str) -> str:
    """
    Loads stylesheet from given path and returns it as string.
    """
    with open(path, "r") as file:
        return file.read()


def set_theme(app, theme_path: str) -> None:
    """
    Sets theme of the application by loading stylesheet from
    given path and applying it to the application.
    """
    with open(theme_path, "r") as file:
        app.setStyleSheet(file.read())
