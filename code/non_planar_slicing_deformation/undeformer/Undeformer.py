import os

from PySide6.QtCore import QObject, Slot, Signal
from typing_extensions import Optional, List, Any

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters
from non_planar_slicing_deformation.undeformer.worker.UndeformerWorker import UndeformerWorker


class Undeformer(QObject):
    """
    Generic class representing an inverse deformation of the gcode (for a mesh deformed by :class:`Deformer`),
    after its sliced
    """

    finishedUndeformation = Signal(Any)  # Real type Signal[List[str]], hack because PySide6 is broken

    def __init__(self, parameters: KeyValueParameters, worker: UndeformerWorker, /) -> None:
        super().__init__()
        self.parameters = parameters
        self.worker: UndeformerWorker = worker
        self.worker.setParent(self)
        self.worker.result.connect(self.setUndeformedGcode)

        self.gcode: Optional[List[str]] = None
        self.undeformedGcode: Optional[List[str]] = None

    def setGcode(self, gcode: List[str]) -> None:
        """
        Set the gcode to undeform
        """
        self.gcode = gcode

    def undeform(self) -> None:
        """
        Do the undeformation using the gcode and the state
        :return: if successful
        """

        if self.gcode is None:
            MAIN_LOGGER.error("Missing gcode, did you forget to call setGcode?")
            return

        self.worker.setArgs(self.gcode, self.getParameters())
        self.worker.start()

    def getUndeformedGcode(self) -> Optional[List[str]]:
        """
        Get the result of the undeformation if its available
        :return: The undeformed gcode if its available, otherwise None
        """
        return self.undeformedGcode

    @Slot()
    def setUndeformedGcode(self, undeformedMesh: Optional[List[str]]) -> None:
        """
        This is meant for the worker to use it
        """
        self.undeformedMesh = undeformedMesh

        self.finishedUndeformation.emit(undeformedMesh)

    def save(self, path: str) -> None:
        """
        Save the undeformed gcode to a file
        """
        if self.undeformedGcode is None:
            MAIN_LOGGER.error("No gcode to save, did you forget to call undeform?")
            return

        if not os.path.splitext(path)[1] == ".gcode":
            MAIN_LOGGER.warning(f"Adding .gcode extension to path '{path}'")
            path += ".gcode"

        with open(path, "wt", encoding="utf-8") as file:
            for line in self.undeformedGcode:
                file.write(f"{line}\n")

    def getParameters(self) -> KeyValueParameters:
        """
        Get the :class:`KeyValueParameters` for this Undeformer
        """
        # TODO move to a superclass
        return self.parameters
