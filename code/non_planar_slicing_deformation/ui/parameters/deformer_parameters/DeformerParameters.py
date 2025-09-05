from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class DeformerParameters(QWidget):
    """
    A UI for settign the parameters of the :class:`Deformer`
    """

    parameterUpdate = Signal()
    """
    Emitted when a parameter is updated
    """
