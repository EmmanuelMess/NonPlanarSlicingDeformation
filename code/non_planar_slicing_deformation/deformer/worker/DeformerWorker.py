from PySide6.QtCore import QThread, Signal, Slot
import pyvista as pv
from typing_extensions import Optional, Any

from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters


class DeformerWorker(QThread):

    result = Signal(Any)  # Real type Signal[Optional[pv.DataSet]], hack because PySide6 is broken

    def __init__(self, /) -> None:
        super().__init__()
        self.mesh: Optional[pv.DataSet] = None
        self.parameters: Optional[KeyValueParameters] = None

    @Slot()
    def setArgs(self, mesh: pv.DataSet, parameters: KeyValueParameters) -> None:
        self.mesh = mesh
        self.parameters = parameters
