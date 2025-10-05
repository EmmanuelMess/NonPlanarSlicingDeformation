from PySide6.QtCore import QThread, Signal, Slot
from typing_extensions import Optional, List, Any

from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters


class UndeformerWorker(QThread):
    result = Signal(Any)  # Real type Signal[List[str]], hack because PySide6 is broken

    def __init__(self, /) -> None:
        super().__init__()
        self.gcode: Optional[List[str]] = None
        self.parameters: Optional[KeyValueParameters] = None

    @Slot()
    def setArgs(self, gcode: List[str], parameters: KeyValueParameters) -> None:
        self.gcode = gcode
        self.parameters = parameters
