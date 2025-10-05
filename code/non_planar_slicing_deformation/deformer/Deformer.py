import os

import pyvista as pv
from PySide6.QtCore import Slot, QObject, Signal
from typing_extensions import Optional, Any

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.KeyValueParameters import KeyValueParameters
from non_planar_slicing_deformation.deformer.worker.DeformerWorker import DeformerWorker


class Deformer(QObject):
    """
    Generic class representing a deformation of the mesh
    """

    finishedDeformation = Signal(Any)  # Real type Signal[Optional[pv.DataSet]], hack because PySide6 is broken

    def __init__(self, parameters: KeyValueParameters, worker: DeformerWorker, /) -> None:
        super().__init__()
        self.parameters = parameters
        self.worker: DeformerWorker = worker
        self.worker.setParent(self)
        self.worker.result.connect(self.setDeformedMesh)

        self.mesh: Optional[pv.DataSet] = None
        self.deformedMesh: Optional[pv.DataSet] = None

    def setMesh(self, mesh: pv.DataSet) -> None:
        """
        Set the input mesh to deform
        """
        self.mesh = mesh

    def save(self, path: str) -> None:
        """
        Save deformed mesh to an stl file
        :param path: A path with ending in a name with or without stl extension
        :return:
        """

        if self.deformedMesh is None:
            MAIN_LOGGER.error("No mesh to save, did you forget to call deform?")
            return

        if not os.path.splitext(path)[1] == ".stl":
            MAIN_LOGGER.warning(f"Adding .stl extension to path '{path}'")
            path += ".stl"

        self.deformedMesh.save(path)

    @Slot(pv.DataSet)
    def setDeformedMesh(self, deformedMesh: Optional[pv.DataSet]) -> None:
        """
        This is meant for the worker to use it
        """
        self.deformedMesh = deformedMesh

        self.finishedDeformation.emit(deformedMesh)

    def deform(self) -> None:
        """
        Deform the mesh, this can fail
        :return: if successful
        """
        if self.mesh is None:
            MAIN_LOGGER.error("Mesh is not set, did you forget to call setMesh?")
            return

        self.worker.setArgs(self.mesh, self.getParameters())
        self.worker.start()

    def getParameters(self) -> KeyValueParameters:
        """
        Get the :class:`KeyValueParameters` for this Deformer
        """
        # TODO move to a superclass
        return self.parameters
