from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class UndeformerParameters(QWidget):
    """
    A UI for setting the parameters of the :class:`Undeformer`
    """

    parameterUpdate = Signal()
    """
    Emitted when a parameter is updated
    """
