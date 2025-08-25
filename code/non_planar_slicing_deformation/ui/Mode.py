from enum import Enum


class Mode(Enum):
    """
    Modes for the application, this changes how the operations deform and undeform are perfomed,
    using different algorithms
    """
    FOUR_AXIS_SIMPLE = 0
    # FOUR_S = 1
    THREE_AXIS = 2
