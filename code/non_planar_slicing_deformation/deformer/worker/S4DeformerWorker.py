import time

import networkx as nx
import numpy as np
import pyvista as pv
import tetgen  # type: ignore
from PySide6.QtCore import Signal
from typing_extensions import cast, Optional, Any, Dict, List

from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.CurrentDeformerState import CurrentDeformerState
from non_planar_slicing_deformation.deformer.s4_deformer import S4Functions
from non_planar_slicing_deformation.deformer.worker.DeformerWorker import DeformerWorker
from non_planar_slicing_deformation.state.S4DeformerState import S4DeformerState


class S4DeformerWorker(DeformerWorker):
    """
    S4 deformer, original implementation by Joshua Bird at https://github.com/jyjblrd/S4_Slicer.
    """

    inputTetResult = Signal(Any)  # Real type Signal[Optional[tetgen.TetGen]], hack because PySide6 is broken
    # Real type Signal[Optional[pv.UnstructuredGrid]], hack because PySide6 is broken
    rotatedTrianglesResult = Signal(Any)
    bottomMeshResult = Signal(Any)  # Real type Signal[Optional[tetgen.TetGen]], hack because PySide6 is broken

    def __init__(self, /) -> None:
        super().__init__()
        self.surface: Optional[pv.PolyData] = None

    def run(self) -> None:
        startTime = time.time()

        MAIN_LOGGER.debug("S4 Deform started")

        if self.mesh is None or self.parameters is None:
            self.result.emit(None)
            return

        # convert to tetrahedral mesh
        input_tet = tetgen.TetGen(np.asarray(self.mesh.vertices), np.asarray(self.mesh.triangles))
        # input_tet.make_manifold() # comment out if not needed
        input_tet.tetrahedralize()
        input_tet = input_tet.grid

        # rotate
        # input_tet = input_tet.rotate_x(-90) # b axis mount

        # scale
        # input_tet = input_tet.scale(1.5)

        # make origin center bottom of bounding box
        x = cast(np.float64, self.parameters["offset x", np.float64])  # TODO deal with None
        y = cast(np.float64, self.parameters["offset y", np.float64])  # TODO deal with None
        z = cast(np.float64, self.parameters["offset z", np.float64])  # TODO deal with None

        # partOffset = np.array([0., 10., 0.]) # z mount
        # partOffset = np.array([-13., -10., 0.]) # bunny
        # partOffset = np.array([60., 0., 0.]) # benchy
        # partOffset = np.array([0., 10., 0.]) # benchy upsidedown tilted
        # partOffset = np.array([0., 10., 0.]) # squirtle
        # partOffset = np.array([-44., 0., 0.]) # b axis mount
        # partOffset = np.array([50., 20., 0.]) # mew
        partOffset = np.array([x, y, z])

        # the larger the weight, the more the rotation field will be smoothed
        neighbourLossWeight = cast(np.float64, self.parameters["neighbour loss weight", np.int64])
        # the maximum overhang angle in degrees
        maxOverhang = cast(np.float64, self.parameters["max overhang", np.float64])
        # the larger the multiplier, the more the rotation field will be rotated
        rotationMultiplier = cast(np.float64, self.parameters["rotation multiplier", np.float64])
        # reduces influence of initial rotation field on non-overhanging
        # tetrahedrons. good when initial rotation field is noisy
        setInitialRotationToZero = cast(bool, self.parameters["set initial rotation to zero", bool])
        initialRotationFieldSmoothing = cast(np.int64, self.parameters["initial rotation field smoothing", np.int64])
        # normally set to 360 unless you get collisions
        maxRotation = np.deg2rad(cast(np.float64, self.parameters["max rotation", np.float64]))
        # normally set to -360 unless you get collisions
        minRotation = np.deg2rad(cast(np.float64, self.parameters["min rotation", np.float64]))
        optimizeRotationIterations = cast(np.int64, self.parameters["optimize rotation iterations", np.int64])
        steepOverhangCompensation = cast(bool, self.parameters["steep overhang compensation", bool])
        calculateDeformationIterations = cast(np.int64, self.parameters["calculate deformation iterations", np.int64])

        x_min, x_max, y_min, y_max, z_min, z_max = input_tet.bounds
        input_tet.points -= np.array([(x_min + x_max) / 2, (y_min + y_max) / 2, z_min]) + partOffset

        MAIN_LOGGER.debug("S4 Deform start fors")
        # find neighbours
        neighbour_types = ["point", "edge", "face"]
        cell_neighbour_dict: Dict[str, Dict[int, List[int]]] = {neighbour_type: {
            face: [] for face in range(input_tet.number_of_cells)} for neighbour_type in neighbour_types}
        for neighbour_type in neighbour_types:
            cell_neighbours = []
            for cell_index in range(input_tet.number_of_cells):
                neighbours = input_tet.cell_neighbors(cell_index, f"{neighbour_type}s")
                for neighbour in neighbours:
                    if neighbour > cell_index:
                        cell_neighbours.append((cell_index, neighbour))
            for face_1, face_2 in np.array(cell_neighbours):
                cell_neighbour_dict[neighbour_type][face_1].append(face_2)
                cell_neighbour_dict[neighbour_type][face_2].append(face_1)

            input_tet.field_data[f"cell_{neighbour_type}_neighbours"] = np.array(cell_neighbours)

        cell_neighbour_graph = nx.Graph()
        cell_centers = input_tet.cell_centers().points
        for edge in input_tet.field_data["cell_point_neighbours"]:  # use point neighbours for best accuracy
            distance = np.linalg.norm(cell_centers[edge[0]] - cell_centers[edge[1]])
            cell_neighbour_graph.add_weighted_edges_from([(edge[0], edge[1], distance)])

        input_tet, bottom_cells_mask, bottom_cells = S4Functions.calculate_tet_attributes(
            input_tet, cell_neighbour_graph)
        MAIN_LOGGER.debug("S4 Deform calculate tet attributes")

        """
        # find bottom cell groups that are connected
        bottom_cell_graph = nx.Graph()
        for cell_index in bottom_cells:
            bottom_cell_graph.add_node(cell_index)
        cell_point_neighbour_dict = cell_neighbour_dict["point"]
        for cell_index in bottom_cells:
            for neighbour in cell_point_neighbour_dict[cell_index]:
                if neighbour in bottom_cells:
                    bottom_cell_graph.add_edge(cell_index, neighbour)

        bottom_cell_groups = [list(x) for x in list(nx.connected_components(bottom_cell_graph))]
        """

        undeformed_tet = input_tet.copy()

        rotation_field = S4Functions.optimize_rotations(
            undeformed_tet,
            cell_neighbour_graph,
            bottom_cells,
            cell_neighbour_dict,
            neighbourLossWeight,
            maxOverhang,
            rotationMultiplier,
            optimizeRotationIterations,
            steepOverhangCompensation,
            initialRotationFieldSmoothing,
            setInitialRotationToZero,
            maxRotation,
            minRotation
            )
        MAIN_LOGGER.debug("S4 Deform rotation field")

        # rotation_field = calculate_initial_rotation_field(tet, maxOverhang, rotationMultiplier)
        undeformed_tet_with_rotated_tetrahedrons = S4Functions.apply_rotation_field_unique_vertices(undeformed_tet,
                                                                                                    rotation_field)
        undeformed_tet_with_rotated_tetrahedrons.cell_data["rotation_field"] = rotation_field
        # new_tet.extract_cells(np.where(rotation_field != 0)[0]).plot()
        rotatedTriangles = undeformed_tet_with_rotated_tetrahedrons  # .plot(scalars="rotation_field")

        MAIN_LOGGER.debug("S4 Deform apply rotation field")

        bottomMesh = undeformed_tet  # .plot(scalars="cell_distance_to_bottom", cpos=[-0.5, -1, -1])

        new_vertices = S4Functions.calculate_deformation(undeformed_tet, rotation_field, calculateDeformationIterations)
        deformed_tet = pv.UnstructuredGrid(undeformed_tet.cells,
                                           np.full(undeformed_tet.number_of_cells, pv.CellType.TETRA), new_vertices)
        self.deformedMesh = deformed_tet  # .plot()

        for key in undeformed_tet.field_data.keys():
            deformed_tet.field_data[key] = undeformed_tet.field_data[key]
        for key in undeformed_tet.cell_data.keys():
            deformed_tet.cell_data[key] = undeformed_tet.cell_data[key]
        deformed_tet = S4Functions.update_tet_attributes(deformed_tet, cell_neighbour_graph)

        # make origin center bottom of bounding box
        x_min, x_max, y_min, y_max, z_min, z_max = deformed_tet.bounds
        offsets_applied = np.array([(x_min + x_max) / 2, (y_min + y_max) / 2, z_min])
        deformed_tet.points -= offsets_applied

        mesh = deformed_tet.extract_surface()

        # TODO check mutithreading safety
        CurrentDeformerState().setState(S4DeformerState(input_tet, deformed_tet, cell_neighbour_graph))

        endTime = time.time()
        MAIN_LOGGER.debug(f"S4 deform time {endTime - startTime}s")

        self.rotatedTrianglesResult.emit(rotatedTriangles)
        self.bottomMeshResult.emit(bottomMesh)
        self.result.emit(mesh)
