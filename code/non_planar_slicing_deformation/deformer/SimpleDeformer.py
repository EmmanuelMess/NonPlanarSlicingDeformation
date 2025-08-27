from typing_extensions import Optional, override, cast

import numpy as np
import pyvista as pv

from common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.CurrentDeformerState import CurrentDeformerState
from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.deformer.Deformer import Deformer
from non_planar_slicing_deformation.state.SimpleDeformerState import SimpleDeformerState


class SimpleDeformer(Deformer):
    """
    Simple defomer, original implementation by Joshua Bird at https://github.com/jyjblrd/Radial_Non_Planar_Slicer.
    """

    def __init__(self) -> None:
        super().__init__(Defaults.simpleDeformerDefaults)

    @override
    def deformImplementation(self, mesh: pv.DataSet) -> Optional[pv.DataSet]:
        mesh = mesh.copy()
        mesh.field_data["faces"] = mesh.faces.reshape(-1, 4)[:, 1:]  # assume all triangles

        # scale mesh
        mesh.points = cast(pv.pyvista_ndarray, mesh.points * 1)

        # center around the middle of the bounding box
        xmin, xmax, ymin, ymax, zmin, _ = mesh.bounds
        mesh.points = cast(pv.pyvista_ndarray, mesh.points - np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, zmin]))
        # mesh.points -= np.array([0, 0, 0]) # optionally offset the part from the center

        mesh.points = cast(pv.pyvista_ndarray, mesh.points[:10])

        # max radius of part
        maxRadius = np.max(np.linalg.norm(mesh.points[:, :2], axis=1))

        # define rotation as a function of radius
        def rotation(radius: np.float64) -> np.float64:
            start = self.getParameters()["start", np.float64]
            end = self.getParameters()["end", np.float64]

            if end < start:
                MAIN_LOGGER.warning(f"End radius {end} is lower than start radius {start}")

            remappedRadius = np.where(radius < start, start, np.where(radius < end, radius, end))

            a = self.getParameters()["zeroth order", np.float64]
            b = self.getParameters()["first order", np.float64]
            c = self.getParameters()["second order", np.float64]
            normalizedRadius = (remappedRadius / maxRadius)
            return a + b * normalizedRadius + c * normalizedRadius ** 2
            # return np.deg2rad(15 + 30 * (radius / maxRadius))  # Use for propeller and tree
            # return np.full_like(radius, np.deg2rad(-40)) # Fixed rotation inwards
            # return np.deg2rad(-40 + 30 * (1 - (radius / maxRadius)) ** 2) # Use for bridge

        # rotate points around max diameter ring
        distances_to_center = np.linalg.norm(mesh.points[:, :2], axis=1)
        translate_upwards = np.hstack([
            np.zeros((len(mesh.points), 2)),
            np.tan(rotation(distances_to_center).reshape(-1, 1)) * distances_to_center.reshape(-1, 1)
            ], dtype=np.float64)

        mesh.points = cast(pv.pyvista_ndarray, mesh.points + translate_upwards)

        # make bottom of part z=0 and center in bound box. remember the offsets for later
        xmin, xmax, ymin, ymax, zmin, _ = mesh.bounds
        offsets_applied = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, zmin])
        mesh.points = cast(pv.pyvista_ndarray, mesh.points - offsets_applied)

        CurrentDeformerState().setState(SimpleDeformerState(rotation, offsets_applied))

        return mesh
