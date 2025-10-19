import open3d as o3d  # type: ignore
import pyvista as pv
import tetgen  # type: ignore
from PySide6.QtCore import Slot
from typing_extensions import override, Optional, Any, cast

from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.deformer.Deformer import Deformer
from non_planar_slicing_deformation.deformer.worker.S4DeformerWorker import S4DeformerWorker


class S4Deformer(Deformer):
    def __init__(self) -> None:
        super().__init__(Defaults.s4DeformerDefaults, S4DeformerWorker())

        self.rotatedTriangles: Optional[pv.UnstructuredGrid] = None
        self.bottomMesh: Optional[tetgen.TetGen] = None

        worker = cast(S4DeformerWorker, self.worker)
        worker.rotatedTrianglesResult.connect(self.onRotatedTriangles)
        worker.bottomMeshResult.connect(self.onBottomMesh)

    @override
    def setMeshPath(self, path: str) -> None:
        """
        Set the input mesh to deform
        """

        loadedMesh: o3d.cpu.pybind.geometry.TriangleMesh = o3d.io.read_triangle_mesh(path)

        self.mesh = loadedMesh

    def getRotatedTriangles(self) -> Optional[pv.UnstructuredGrid]:
        return self.rotatedTriangles

    def getBottomMesh(self) -> Optional[tetgen.TetGen]:
        return self.bottomMesh

    @Slot(Any)
    def onRotatedTriangles(self, result: Any) -> None:
        if result is None:
            self.rotatedTriangles = None
        else:
            self.rotatedTriangles = cast(pv.UnstructuredGrid, result).copy(deep=True)

    @Slot(Any)
    def onBottomMesh(self, result: Any) -> None:
        if result is None:
            self.bottomMesh = None
        else:
            self.bottomMesh = cast(tetgen.TetGen, result).copy(deep=True)
