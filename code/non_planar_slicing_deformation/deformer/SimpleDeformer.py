from typing_extensions import Optional, override, cast

import numpy as np
import pyvista as pv

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
        max_radius = np.max(np.linalg.norm(mesh.points[:, :2], axis=1))

        # define rotation as a function of radius
        def rotation(radius: np.float64) -> np.float64:
            return self.getParameters()["radius", float] * (radius / max_radius)
            # return np.deg2rad(15 + 30 * (radius / max_radius))  # Use for propeller and tree
            # return np.full_like(radius, np.deg2rad(-40)) # Fixed rotation inwards
            # return np.deg2rad(-40 + 30 * (1 - (radius / max_radius)) ** 2) # Use for bridge

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
