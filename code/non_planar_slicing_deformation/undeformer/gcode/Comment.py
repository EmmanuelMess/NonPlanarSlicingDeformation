from dataclasses import dataclass


@dataclass
class Comment:
    """
    Represents the text of a comment of gcode
    """
    text: str
