from typing_extensions import Optional, override, cast

import numpy as np
import pyvista as pv

from non_planar_slicing_deformation.configuration.CurrentDeformerState import CurrentDeformerState
from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.deformer.Deformer import Deformer
from non_planar_slicing_deformation.state.ThreeAxisDeformerState import ThreeAxisDeformerState


class ThreeAxisDeformer(Deformer):
    """
    Simple defomer, original implementation by Joshua Bird at https://github.com/jyjblrd/Radial_Non_Planar_Slicer
    modified to work with a common 3 axis 3d printer
    """

    def __init__(self) -> None:
        super().__init__(Defaults.threeAxisDeformerDefaults)

    @override
    def deformImplementation(self, mesh: pv.DataSet) -> Optional[pv.DataSet]:
        mesh = mesh.copy()

        # TODO check all tris
        mesh.field_data["faces"] = mesh.faces.reshape(-1, 4)[:, 1:]  # assume all triangles
        points = mesh.points

        firstOrder: float = self.getParameters()["first order", float]
        secondOrder: float = self.getParameters()["second order", float]

        translationX: float = self.getParameters()["x translation", float] * np.max(points[:, 0])
        translationY: float = self.getParameters()["y translation", float] * np.max(points[:, 1])

        translationVector = np.array([
            translationX,
            translationY,
            0.0,
            ])

        radius = np.sqrt((points[:, 0] - translationVector[0]) ** 2 + (points[:, 1] - translationVector[1]) ** 2)

        points[:, 2] += firstOrder * radius + secondOrder * radius ** 2

        mesh.points = cast(pv.pyvista_ndarray, points)

        CurrentDeformerState().setState(
            ThreeAxisDeformerState(firstOrder, secondOrder, translationX, translationY)
            )

        return mesh
