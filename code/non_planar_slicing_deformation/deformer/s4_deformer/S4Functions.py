import base64
import pickle

from numpy.linalg import svd
import networkx as nx
import pyvista as pv
from pyvista import DataSet
from pyvista.plotting import _vtk
from typing_extensions import Final, Any, Tuple, Dict, List, cast, Set

import numpy as np
import scipy
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation as R

"""
These are the S4 functions, that should be renamed and moved to other places
"""

up_vector: np.ndarray = np.array([0, 0, 1])


def encode_object(obj: Any) -> str:
    return base64.b64encode(pickle.dumps(obj)).decode('utf-8')


def decode_object(encoded_str: str) -> Any:
    return pickle.loads(base64.b64decode(encoded_str))


def update_tet_attributes(unstructuredGrid: pv.UnstructuredGrid, cell_neighbour_graph: nx.Graph) -> pv.UnstructuredGrid:
    """
    Calculate face normals, face centers, cell centers, and overhang angles for each cell in the tetrahedral mesh.
    """

    surface_mesh = unstructuredGrid.extract_surface()
    cell_to_face = decode_object(unstructuredGrid.field_data["cell_to_face"])  # type: ignore  # HACK type is correct

    # put general data in field_data for easy access
    cells = unstructuredGrid.cells.reshape(-1, 5)[:, 1:]  # assume all cells have 4 vertices
    unstructuredGrid.add_field_data(cells, "cells")
    cell_vertices = unstructuredGrid.points
    unstructuredGrid.add_field_data(cell_vertices, "cell_vertices")
    faces = surface_mesh.faces.reshape(-1, 4)[:, 1:]  # assume all faces have 3 vertices
    unstructuredGrid.add_field_data(faces, "faces")
    face_vertices = surface_mesh.points
    unstructuredGrid.add_field_data(face_vertices, "face_vertices")

    face_normal = np.full((unstructuredGrid.number_of_cells, 3), np.nan)
    surface_mesh_face_normals = surface_mesh.face_normals
    for cell_index, face_indices in cell_to_face.items():
        face_normals = surface_mesh_face_normals[face_indices]
        # get the normal facing the most down
        most_down_normal_index = np.argmin(face_normals[:, 2])
        face_normal[cell_index] = face_normals[most_down_normal_index]
    unstructuredGrid.cell_data['face_normal'] =\
        face_normal / np.linalg.norm(face_normal, axis=1)[:, None]

    face_center = np.full((unstructuredGrid.number_of_cells, 3), np.nan)
    surface_mesh_cell_centers = surface_mesh.cell_centers().points
    for cell_index, face_indices in cell_to_face.items():
        face_centers = surface_mesh_cell_centers[face_indices]
        # get the normal facing the most down
        most_down_center_index = np.argmin(face_centers[:, 2])
        face_center[cell_index] = face_centers[most_down_center_index]

    unstructuredGrid.cell_data['face_center'] = face_center

    unstructuredGrid.cell_data["cell_center"] = unstructuredGrid.cell_centers().points

    # calculate bottom cells
    bottom_cell_threshold = np.nanmin(unstructuredGrid.cell_data['face_center'][:, 2]) + 0.3
    bottom_cells_mask = unstructuredGrid.cell_data['face_center'][:, 2] < bottom_cell_threshold
    unstructuredGrid.cell_data['is_bottom'] = bottom_cells_mask
    bottom_cells = np.where(bottom_cells_mask)[0]

    face_normals = unstructuredGrid.cell_data['face_normal'].copy()
    face_normals[bottom_cells_mask] = np.nan  # make bottom faces not angled
    overhang_angle = np.arccos(np.dot(face_normals, up_vector))
    unstructuredGrid.cell_data['overhang_angle'] = overhang_angle

    overhang_direction = face_normals[:, :2].copy()
    overhang_direction /= np.linalg.norm(overhang_direction, axis=1)[:, None]
    unstructuredGrid.cell_data['overhang_direction'] = overhang_direction

    # calculate if cell will print in air by seeing if any cell centers along path to base are higher
    IN_AIR_THRESHOLD = 1
    unstructuredGrid.cell_data['in_air'] = np.full(unstructuredGrid.number_of_cells, False)

    _, paths_to_bottom = nx.multi_source_dijkstra(cell_neighbour_graph, set(bottom_cells))

    # put it in cell data
    path_to_bottom = np.full((unstructuredGrid.number_of_cells, np.max([len(x) for x in paths_to_bottom.values()])), -1)
    for cell_index, path in paths_to_bottom.items():
        path_to_bottom[cell_index, :len(path)] = path
    unstructuredGrid.cell_data['path_to_bottom'] = path_to_bottom

    # calculate if cell is in air
    for cell_index in range(unstructuredGrid.number_of_cells):
        path_to_bottom = paths_to_bottom[cell_index]
        if len(path_to_bottom) > 1:
            cell_heights = unstructuredGrid.cell_data['cell_center'][path_to_bottom, 2]
            if np.any(cell_heights > unstructuredGrid.cell_data['cell_center'][cell_index, 2] + IN_AIR_THRESHOLD):
                unstructuredGrid.cell_data['in_air'][cell_index] = True

    return unstructuredGrid


def calculate_tet_attributes(tet: pv.UnstructuredGrid, cell_neighbour_graph: nx.Graph) \
        -> Tuple[pv.UnstructuredGrid, np.ndarray, np.ndarray]:
    """
    Calculate shared vertices between cells, cell to face & face to cell relations,
    and bottom cells of the tetrahedral mesh.
    """

    surface_mesh = tet.extract_surface()

    # put general data in field_data for easy access
    cells = tet.cells.reshape(-1, 5)[:, 1:]  # assume all cells have 4 vertices
    tet.add_field_data(cells, "cells")
    cell_vertices = tet.points
    tet.add_field_data(cell_vertices, "cell_vertices")
    faces = surface_mesh.faces.reshape(-1, 4)[:, 1:]  # assume all faces have 3 vertices
    tet.add_field_data(faces, "faces")
    face_vertices = surface_mesh.points
    tet.add_field_data(face_vertices, "face_vertices")

    # calculate shared vertices
    shared_vertices = []
    for cell_1, cell_2 in tet.field_data["cell_point_neighbours"]:
        shared_vertices_these_faces = np.intersect1d(cells[cell_1], cells[cell_2])
        for vertex in shared_vertices_these_faces:
            shared_vertices.append({
                "cell_1_index": cell_1,
                "cell_2_index": cell_2,
                "cell_1_vertex_index": np.where(cells[cell_1] == vertex)[0][0],
                "cell_2_vertex_index": np.where(cells[cell_2] == vertex)[0][0],
                })

    # calculate cell to face & face to cell relations
    cell_to_face = {}
    face_to_cell: Dict[int, List[int]] = {face_index: [] for face_index in range(len(faces))}
    cell_to_face_vertices = {}
    face_to_cell_vertices = {}
    for cell_vertex_index, cell_vertex in enumerate(tet.field_data["cell_vertices"].reshape(-1, 3)):
        face_vertex_index = np.where((face_vertices == cell_vertex).all(axis=1))[0]
        if len(face_vertex_index) == 1:
            cell_to_face_vertices[cell_vertex_index] = face_vertex_index[0]
            face_to_cell_vertices[face_vertex_index[0]] = cell_vertex_index

    for cell_index, cell in enumerate(tet.field_data["cells"]):
        face_vertex_indices = [cell_to_face_vertices[cell_vertex_index]
                               for cell_vertex_index in cell if cell_vertex_index in cell_to_face_vertices]
        if len(face_vertex_indices) >= 3:
            extracted = surface_mesh.extract_points(face_vertex_indices, adjacent_cells=False)
            if extracted.number_of_cells >= 1:
                cell_to_face[cell_index] = list(extracted.cell_data['vtkOriginalCellIds'])
                for face_index in extracted.cell_data['vtkOriginalCellIds']:
                    face_to_cell[face_index].append(cell_index)

    tet.add_field_data(encode_object(cell_to_face), "cell_to_face")  # type: ignore  # str is a valid parameter type
    tet.add_field_data(encode_object(face_to_cell), "face_to_cell")  # type: ignore  # str is a valid parameter type

    # calculate has_face attribute
    tet.cell_data['has_face'] = np.zeros(tet.number_of_cells)
    for cell_index, face_indices in cell_to_face.items():
        tet.cell_data['has_face'][cell_index] = 1

    tet = update_tet_attributes(tet, cell_neighbour_graph)

    # calculate bottom cells
    bottom_cells_mask = tet.cell_data['is_bottom']
    bottom_cells = np.where(bottom_cells_mask)[0]

    # cast use is a HACK, broken type equivalence
    tet.cell_data['overhang_angle'][cast(pv.pyvista_ndarray, bottom_cells)] = np.nan

    return tet, cast(np.ndarray, bottom_cells_mask), bottom_cells


def planeFit(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    p, n = planeFit(points)

    Given an array, points, of shape (d,...)
    representing points in d-dimensional space,
    fit an d-dimensional plane to the points.
    Return a point, p, on the plane (the point-cloud centroid),
    and the normal, n.
    """
    points = np.reshape(points, (np.shape(points)[0], -1))
    assert points.shape[0] <= points.shape[1], "There are only {} points in {} dimensions.".format(
        points.shape[1], points.shape[0])
    ctr = points.mean(axis=1)
    x = points - ctr[:, np.newaxis]
    M = np.dot(x, x.T)
    return ctr, svd(M)[0][:, -1]


def calculate_path_length_to_base_gradient(  # noqa: C901
        tet: pv.UnstructuredGrid,
        cell_neighbour_graph: nx.Graph,
        bottom_cells: np.ndarray,
        cell_neighbour_dict: Dict[str, Dict[int, List[int]]],
        maxOverhang: np.float64,
        initialRotationFieldSmoothing: np.int64,
        setInitialRotationToZero: bool
) -> np.ndarray:
    """
    Calculate the path length to base gradient for each cell in the tetrahedral mesh
    with respect to the radial direction. This is used to determine the optimal rotation direction for each cell.

    returns: path_length_to_base_gradient. A scalar for each cell in the tetrahedral mesh.
     This is the gradient in the radial direction of the path length to the closest bottom cell.
    """

    # calculate initial rotation direction for each face
    # this is a scalar with respect to the radial direction. ie the vector pointing to the cell center
    path_length_to_base_gradient = np.zeros((tet.number_of_cells))

    # find the path length for every overhang cell to a bottom cell
    cell_distance_to_bottom = np.empty((tet.number_of_cells))
    cell_distance_to_bottom[:] = np.nan
    distances_to_bottom, paths_to_bottom = nx.multi_source_dijkstra(cell_neighbour_graph, set(
        bottom_cells))  # set([x[0] for x in tet.field_data["bottom_cell_groups"]]))
    closest_bottom_cell_indices = np.zeros((tet.number_of_cells), dtype=int)
    for cell_index in range(tet.number_of_cells):
        face_normal = tet.cell_data["face_normal"][cell_index]

        cell_is_overhang = np.arccos(np.dot(face_normal, [0, 0, 1])) > np.deg2rad(90 + maxOverhang)
        if cell_is_overhang and cell_index not in bottom_cells:
            closest_bottom_cell_indices[cell_index] = paths_to_bottom[cell_index][0]
            cell_distance_to_bottom[cell_index] = distances_to_bottom[cell_index]

    tet.cell_data["cell_distance_to_bottom"] = cell_distance_to_bottom

    # calculate the gradient of path length to base for each cell
    for cell_index in range(tet.number_of_cells):
        if not np.isnan(cell_distance_to_bottom[cell_index]):
            edge_cell = cell_neighbour_dict["edge"][cell_index]
            local_cells = np.hstack((edge_cell, cell_index))
            # add neighbours neighbours
            # local_cells = neighbours.copy()
            # for neighbour in neighbours:
            #     local_cells.extend(cell_neighbour_dict["point"][neighbour])
            # local_cells = np.array(list(set(local_cells)))

            local_cell_path_lengths = np.array([cell_distance_to_bottom[local_cell] for local_cell in local_cells])

            # remove neighbours with path length of nan
            local_cells = np.array(local_cells)[~np.isnan(local_cell_path_lengths)]
            local_cell_path_lengths = local_cell_path_lengths[~np.isnan(local_cell_path_lengths)]

            # if there are less than 3 neighbours with path length, roll to the closest bottom cell
            if len(local_cell_path_lengths) < 3:
                location_to_roll_to = tet.cell_data["cell_center"][closest_bottom_cell_indices[cell_index], :2]

                direction_to_bottom = location_to_roll_to - tet.cell_data["cell_center"][cell_index, :2]
                direction_to_bottom /= np.linalg.norm(direction_to_bottom)

                cell_center = tet.cell_data["cell_center"][cell_index, :2].copy()
                cell_center /= np.linalg.norm(cell_center)

                optimal_rotation_direction = np.dot(cell_center, direction_to_bottom) / \
                    np.abs(np.dot(cell_center, direction_to_bottom))
                if np.isnan(optimal_rotation_direction):
                    optimal_rotation_direction = 0

                path_length_to_base_gradient[cell_index] = optimal_rotation_direction

            # if there are 3 or more neighbours with path length, calculate the gradient in the radial direction
            # and use that as the optimal rotation direction
            else:
                points = np.hstack((tet.cell_data["cell_center"][local_cells, :2], local_cell_path_lengths[:, None]))
                _, plane_normal = planeFit(points.T)

                cell_center_direction_norm = np.linalg.norm(tet.cell_data["cell_center"][cell_index, :2])
                cell_center_direction_normalized = (
                    tet.cell_data["cell_center"][cell_index, :2] / cell_center_direction_norm
                    )
                gradient_in_radial_direction = np.dot(cell_center_direction_normalized, plane_normal[:2])

                # if the gradient is nan, use the average of the neighbours
                if np.isnan(gradient_in_radial_direction):
                    gradient_in_radial_direction = np.mean(
                        path_length_to_base_gradient[local_cells][~np.isnan(path_length_to_base_gradient[local_cells])])
                    if np.isnan(gradient_in_radial_direction):
                        gradient_in_radial_direction = 0

                path_length_to_base_gradient[cell_index] = gradient_in_radial_direction

    # smooth path_length_to_base_gradient with neighbours
    # not needed because we do neighbour difference minimization in the optimization step?
    if initialRotationFieldSmoothing != 0:
        for i in range(initialRotationFieldSmoothing):
            smoothed_path_length_to_base_gradient = np.zeros((tet.number_of_cells))
            for cell_index in range(tet.number_of_cells):
                if path_length_to_base_gradient[cell_index] != 0:
                    neighbours = cell_neighbour_dict["point"][cell_index]
                    neighbours_copy = neighbours.copy()
                    for neighbour in neighbours:
                        neighbours_copy.extend(cell_neighbour_dict["point"][neighbour])
                    local_cells_set = np.array(list(set(neighbours_copy)))
                    local_cells = local_cells_set[path_length_to_base_gradient[local_cells_set] != 0]
                    smoothed_path_length_to_base_gradient[cell_index] = np.mean(
                        path_length_to_base_gradient[local_cells])

        path_length_to_base_gradient = smoothed_path_length_to_base_gradient

    # replace 0 with nan
    if not setInitialRotationToZero:
        path_length_to_base_gradient[path_length_to_base_gradient == 0] = np.nan
    tet.cell_data["path_length_to_base_gradient"] = path_length_to_base_gradient  # very sexy

    return path_length_to_base_gradient


def calculate_initial_rotation_field(tet: pv.UnstructuredGrid, cell_neighbour_graph: nx.Graph,
                                     bottom_cells: np.ndarray,
                                     cell_neighbour_dict: Dict[str, Dict[int, List[int]]],
                                     MAX_OVERHANG: np.float64,
                                     ROTATION_MULTIPLIER: np.float64, STEEP_OVERHANG_COMPENSATION: bool,
                                     INITIAL_ROTATION_FIELD_SMOOTHING: np.int64,
                                     SET_INITIAL_ROTATION_TO_ZERO: bool, MAX_POS_ROTATION: np.float64,
                                     MAX_NEG_ROTATION: np.float64) -> np.ndarray:
    """
    Calculate the initial rotation field for each cell in the tetrahedral mesh to make overhangs less than MAX_OVERHANG.
    The direction of rotation ensures the part is printable.
    """

    # create initial rotation field rotating faces to be in safe printing angle
    initial_rotation_field = np.full((tet.number_of_cells), np.nan)
    initial_rotation_field = np.abs(np.deg2rad(90 + MAX_OVERHANG) - tet.cell_data['overhang_angle'])

    path_length_to_base_gradient = calculate_path_length_to_base_gradient(
        tet, cell_neighbour_graph, bottom_cells, cell_neighbour_dict, MAX_OVERHANG, INITIAL_ROTATION_FIELD_SMOOTHING,
        SET_INITIAL_ROTATION_TO_ZERO
        )

    # if path_length_to_base_gradient is different to the cell's overhang direction, it needs to be rotated an
    # additional amount (its overhang angle) to make it go the right way
    # Put behind a flag because it is normally not needed, and buggy/finnicky
    # Can try enable it for models with very steep overhangs (>90 degrees) (not common)
    if STEEP_OVERHANG_COMPENSATION:
        initial_rotation_field[tet.cell_data["in_air"]] += 2 * \
            (np.deg2rad(180) - tet.cell_data['overhang_angle'][tet.cell_data["in_air"]])

    # # Apply the path_length_to_base_gradient (optimal overhang direction) to the initial rotation field
    initial_rotation_field *= path_length_to_base_gradient

    # apply rotation multiplier
    initial_rotation_field = np.clip(initial_rotation_field * ROTATION_MULTIPLIER, -np.deg2rad(360), np.deg2rad(360))

    # clip to max rotation
    initial_rotation_field = np.clip(initial_rotation_field, MAX_NEG_ROTATION, MAX_POS_ROTATION)

    tet.cell_data["initial_rotation_field"] = initial_rotation_field

    return initial_rotation_field


def calculate_rotation_matrices(tet: pv.UnstructuredGrid, rotation_field: np.ndarray) -> np.ndarray:
    """
    Calculate the rotation matrices for each cell in the tetrahedral mesh given the scalar
    rotation field that gives a rotation for each cell. Cells are rotated around the axis
    perpendicular to the radial direction and the z-axis.
    """

    # create rotation matrix from theta around axis
    tangential_vectors = np.cross(np.array([0, 0, 1]), tet.cell_data["cell_center"][:, :2])
    # normalize
    tangential_vectors /= np.linalg.norm(tangential_vectors, axis=1)[:, None]
    # replace nan with [1,0,0]
    tangential_vectors[np.isnan(tangential_vectors).any(axis=1)] = [1, 0, 0]

    rotation_matrices = R.from_rotvec(rotation_field[:, None] * tangential_vectors).as_matrix()

    return rotation_matrices


def calculate_unique_vertices_rotated(tet: pv.UnstructuredGrid, rotation_field: np.ndarray) -> np.ndarray:
    """
    Calculate the vertices of a tetrahedral mesh after rotating each cell by the rotation field.
    Vertices are unique: they are not shared between cells.
    """

    rotation_matrices = calculate_rotation_matrices(tet, rotation_field)

    # rotate each face by the rotation field around its center
    unique_vertices = np.zeros((tet.number_of_cells, 4, 3))
    for cell_index, cell in enumerate(tet.field_data["cells"]):
        unique_vertices[cell_index] = tet.field_data["cell_vertices"][cell]

    cell_centers = tet.cell_data["cell_center"]

    unique_vertices_rotated = (
        cell_centers.reshape(-1, 1, 3, 1)
        + rotation_matrices.reshape(-1, 1, 3, 3)
        @ (unique_vertices.reshape(-1, 4, 3, 1) - cell_centers.reshape(-1, 1, 3, 1))
        )
    # unique_vertices_rotated = rotation_matrices.reshape(-1, 1, 3, 3) @ unique_vertices.reshape(-1, 4, 3, 1)

    return unique_vertices_rotated


def apply_rotation_field_unique_vertices(tet: pv.UnstructuredGrid, rotation_field: np.ndarray) -> pv.UnstructuredGrid:
    """
    Apply the rotation field to the tetrahedral mesh and return a new tetrahedral mesh.
    Vertices are unique: they are not shared between cells.
    """

    unique_vertices_rotated = calculate_unique_vertices_rotated(tet, rotation_field)

    unique_cells = np.zeros((tet.number_of_cells, 5), dtype=int)
    unique_cells[:, 0] = 4
    unique_cells[:, 1:] = np.arange(tet.number_of_cells * 4).reshape(-1, 4)

    new_tet = pv.UnstructuredGrid(unique_cells.flatten(), np.full(
        tet.number_of_cells, pv.CellType.TETRA), unique_vertices_rotated.reshape(-1, 3))

    return new_tet


def apply_rotation_field(tet: pv.UnstructuredGrid, rotation_field: np.ndarray) -> pv.UnstructuredGrid:
    """
    Apply the rotation field to the tetrahedral mesh and return a new tetrahedral mesh.
    Vertices are shared between cells, so the surface is closed and smooth.
    """

    new_vertices = np.zeros((tet.number_of_points, 3))
    vertices_count = np.zeros((tet.number_of_points))
    for cell in tet.field_data["cells"]:
        vertices_count[cell] += 1

    unique_vertices_rotated = calculate_unique_vertices_rotated(tet, rotation_field)

    for cell_index, vertices in enumerate(unique_vertices_rotated):
        for i, vertex in enumerate(vertices):
            new_vertices[tet.field_data["cells"][cell_index, i]] += vertex.T[0] / \
                vertices_count[tet.field_data["cells"][cell_index][i]]

    new_tet = pv.UnstructuredGrid(tet.cells, np.full(tet.number_of_cells, pv.CellType.TETRA), new_vertices)

    return new_tet


def optimize_rotations(tet: pv.UnstructuredGrid, cell_neighbour_graph: nx.Graph,
                       bottom_cells: np.ndarray, cell_neighbour_dict: Dict[str, Dict[int, List[int]]],
                       NEIGHBOUR_LOSS_WEIGHT: np.float64,
                       MAX_OVERHANG: np.float64,
                       ROTATION_MULTIPLIER: np.float64, ITERATIONS: np.int64, STEEP_OVERHANG_COMPENSATION: bool,
                       INITIAL_ROTATION_FIELD_SMOOTHING: np.int64,
                       SET_INITIAL_ROTATION_TO_ZERO: bool, MAX_POS_ROTATION: np.float64,
                       MAX_NEG_ROTATION: np.float64) -> np.ndarray:
    """
    Optimize the rotation field for each cell in the tetrahedral mesh to make overhangs less
    than MAX_OVERHANG while keeping the rotation field smooth.
    """

    initial_rotation_field = calculate_initial_rotation_field(
        tet, cell_neighbour_graph, bottom_cells, cell_neighbour_dict, MAX_OVERHANG, ROTATION_MULTIPLIER,
        STEEP_OVERHANG_COMPENSATION, INITIAL_ROTATION_FIELD_SMOOTHING, SET_INITIAL_ROTATION_TO_ZERO, MAX_POS_ROTATION,
        MAX_NEG_ROTATION
        )
    num_cells_with_initial_rotation = np.sum(~np.isnan(initial_rotation_field))

    def objective_function(rotation_field: np.ndarray) -> np.ndarray:
        """
        Objective function to minimize the neighbour losses and initial rotation losses.
        """
        # Compute neighbour losses using vectorized operations
        cell_face_neighbours = tet.field_data["cell_face_neighbours"]
        neighbour_differences = rotation_field[cell_face_neighbours[:, 0]] - rotation_field[cell_face_neighbours[:, 1]]
        neighbour_losses = NEIGHBOUR_LOSS_WEIGHT * neighbour_differences**2

        # Compute the initial rotation losses
        valid_cell_indices = np.where(~np.isnan(initial_rotation_field))[0]  # np.where(overhanging_mask)[0]
        initial_rotation_losses = (rotation_field[valid_cell_indices] - initial_rotation_field[valid_cell_indices])**2

        # Return the concatenated losses
        return np.concatenate((neighbour_losses, initial_rotation_losses))

    def objective_jacobian(rotation_field: np.ndarray) -> scipy.sparse.csr_matrix:
        # Initialize the sparse matrix with LIL format for efficient row-wise operations
        cell_face_neighbours = tet.field_data["cell_face_neighbours"]
        jac = lil_matrix(
            (len(cell_face_neighbours)
             + num_cells_with_initial_rotation,
             tet.number_of_cells),
            dtype=np.float32)

        # Vectorized computation for neighbour loss derivatives
        cell_1 = cell_face_neighbours[:, 0]
        cell_2 = cell_face_neighbours[:, 1]

        # Compute the differences
        differences = rotation_field[cell_1] - rotation_field[cell_2]

        # Fill in the Jacobian for the first derivative of the neighbour loss function
        jac[range(len(cell_face_neighbours)), cell_1] = 2 * NEIGHBOUR_LOSS_WEIGHT * differences
        jac[range(len(cell_face_neighbours)), cell_2] = -2 * NEIGHBOUR_LOSS_WEIGHT * differences

        # Vectorized computation for initial rotation loss derivatives
        valid_cell_indices = np.where(~np.isnan(initial_rotation_field))[0]  # np.where(overhanging_mask)[0]

        # Fill in the Jacobian for the first derivative of the initial rotation loss function
        jac[len(cell_face_neighbours) + np.arange(len(valid_cell_indices)), valid_cell_indices] = \
            2 * (rotation_field[valid_cell_indices] - initial_rotation_field[valid_cell_indices])

        # print("Jacobian time:", time.time() - start_time)
        # Convert the LIL matrix to CSR format for efficient computations in further steps
        return jac.tocsr()

    def jac_sparsity() -> scipy.sparse.csr_matrix:
        cell_face_neighbours = tet.field_data["cell_face_neighbours"]
        sparsity = lil_matrix(
            (len(cell_face_neighbours)
             + num_cells_with_initial_rotation,
             tet.number_of_cells),
            dtype=np.int8)

        for i, (cell_1, cell_2) in enumerate(cell_face_neighbours):
            sparsity[i, cell_1] = 1
            sparsity[i, cell_2] = 1

        valid_cell_indices = np.where(~np.isnan(initial_rotation_field))[0]  # np.where(overhanging_mask)[0]
        i = 0
        for cell_index, initial_rotation in enumerate(initial_rotation_field):
            if cell_index in valid_cell_indices:
                sparsity[len(cell_face_neighbours) + i, cell_index] = 1
                i += 1

        return sparsity.tocsr()

    smoothed_rotation_field = np.zeros((tet.number_of_cells))

    # Optimization process to smooth the initial rotation field
    result = scipy.optimize.least_squares(
        objective_function, smoothed_rotation_field, jac=objective_jacobian, max_nfev=ITERATIONS,
        jac_sparsity=jac_sparsity(), verbose=1, method='trf', ftol=1e-6,
        )

    return result.x


# TODO move this somewhere else
# the N matrix centers the vertices of a tetrahedron around the origin
N: Final[np.ndarray] = np.eye(4) - 1 / 4 * np.ones((4, 4))


def calculate_deformation(tet: pv.UnstructuredGrid, rotation_field: np.ndarray, ITERATIONS: np.int64) -> np.ndarray:
    """
    Try to find the optimal deformation of the tetrahedral mesh to make cells have the same rotation as
    the given rotation field.

    Our parameters are the vertices of the deformed mesh.
    """

    new_vertices = tet.points.copy()

    params = new_vertices.flatten()

    rotation_matrices = calculate_rotation_matrices(tet, rotation_field)

    # Extract old vertices for all cells
    old_vertices = tet.field_data["cell_vertices"][tet.field_data["cells"]]
    # Apply the transformation for all cells
    old_vertices_transformed = np.einsum('ijk,ikl->ijl', rotation_matrices, (N @ old_vertices).transpose(0, 2, 1))

    def objective_function(params: np.ndarray) -> np.ndarray:
        new_vertices = params[:tet.number_of_points * 3].reshape(-1, 3)

        # Apply transformation for the new vertices
        new_vertices_transformed = (N @ new_vertices[tet.field_data["cells"]]).transpose(0, 2, 1)

        # Calculate position compatibility loss using vectorized operations
        position_losses = np.linalg.norm(new_vertices_transformed - old_vertices_transformed, axis=(1, 2))**2

        # print(f"Objective function took {time.time() - start_time} seconds")
        return position_losses

    def objective_jacobian(params: np.ndarray) -> scipy.sparse.csr_matrix:
        # Initialize Jacobian matrix
        J = lil_matrix((tet.number_of_cells, len(params)), dtype=np.float32)

        # Extract parameters
        new_vertices = params[:tet.number_of_points * 3].reshape(-1, 3)

        # Extract old vertices for all cells
        # old_vertices = tet.field_data["cell_vertices"][tet.field_data["cells"]]

        # Apply the transformation for old and new vertices
        new_vertices_transformed = (N @ new_vertices[tet.field_data["cells"]]).transpose(0, 2, 1)

        # Compute the difference between transformed new and old vertices
        diff = new_vertices_transformed - old_vertices_transformed  # shape: (num_cells, 3, num_vertices_per_cell)

        # Reshape diff for easier broadcasting
        diff = diff.transpose(0, 2, 1)  # shape: (num_cells, num_vertices_per_cell, 3)

        # Now, for each cell, update the corresponding rows in the Jacobian
        cell_indices = np.repeat(np.arange(tet.number_of_cells), len(
            tet.field_data["cells"][0]))  # Cell indices repeated per vertex
        vertex_indices = np.ravel(tet.field_data["cells"])  # Flatten the cell-to-vertex mapping

        # For each component x, y, z in the vertex, update the Jacobian
        for dim in range(3):
            J[cell_indices, vertex_indices * 3 + dim] = 2 * diff[:, :, dim].ravel()

        # print(f"Objective jacobian took {time.time() - start_time} seconds")
        return J.tocsr()

    def jac_sparsity() -> scipy.sparse.csr_matrix:
        sparsity = lil_matrix((tet.number_of_cells, len(params)), dtype=np.int8)

        cell_indices = np.repeat(np.arange(tet.number_of_cells), len(tet.field_data["cells"][0]))
        vertex_indices = np.ravel(tet.field_data["cells"])

        for dim in range(3):
            sparsity[cell_indices, vertex_indices * 3 + dim] = 1

        return sparsity.tocsr()

    result = scipy.optimize.least_squares(objective_function,
                                          params,
                                          max_nfev=ITERATIONS,
                                          verbose=1,
                                          jac=objective_jacobian,
                                          jac_sparsity=jac_sparsity(),
                                          method='trf',
                                          x_scale='jac',
                                          )

    return result.x[:tet.number_of_points * 3].reshape(-1, 3)


def tetrahedron_volume(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray) -> np.float64:
    """
    Calculate the volume of the tetrahedron formed by four points
    """

    mat = np.vstack([p2 - p1, p3 - p1, p4 - p1])
    return np.abs(np.linalg.det(mat)) / 6


def calc_barycentric_coordinates(tet_a: np.ndarray, tet_b: np.ndarray, tet_c: np.ndarray, tet_d: np.ndarray,
                                 point: np.ndarray) -> np.ndarray:
    """
    Calculate the barycentric coordinates of a point in a tetrahedron. This is used to interpolate
    parameters from the vertices of the tetrahedron to a point within the tetrhedron.
    """

    total_volume = tetrahedron_volume(tet_a, tet_b, tet_c, tet_d)

    if total_volume == 0:
        raise ValueError("The points do not form a valid tetrahedron (zero volume).")

    # Calculate the sub-volumes for each face
    vol_a = tetrahedron_volume(point, tet_b, tet_c, tet_d)
    vol_b = tetrahedron_volume(point, tet_a, tet_c, tet_d)
    vol_c = tetrahedron_volume(point, tet_a, tet_b, tet_d)
    vol_d = tetrahedron_volume(point, tet_a, tet_b, tet_c)

    # Calculate barycentric coordinates as the ratio of sub-volumes to total volume
    lambda_a = vol_a / total_volume
    lambda_b = vol_b / total_volume
    lambda_c = vol_c / total_volume
    lambda_d = vol_d / total_volume

    # The barycentric coordinates should sum to 1
    return np.array([lambda_a, lambda_b, lambda_c, lambda_d])


def project_point_onto_plane(plane_x_axis: np.ndarray, plane_y_axis: np.ndarray, point: np.ndarray) -> np.ndarray:
    projected_x = np.sum(plane_x_axis * point, axis=1)
    projected_y = np.sum(plane_y_axis * point, axis=1)

    return np.array([projected_x, projected_y]).T


def allCellNeighbours(dataset: DataSet) -> Dict[str, Dict[int, Set[int]]]:
    """
    This is equivalent to running Cells.cell_neighbors on all cells of the DataSet
    This method is NOT THREAD SAFE
    :return:
    """

    # Build links as recommended:
    # https://vtk.org/doc/nightly/html/classvtkPolyData.html#adf9caaa01f72972d9a986ba997af0ac7
    if hasattr(dataset, 'BuildLinks'):
        dataset.BuildLinks()

    result: Dict[str, Dict[int, Set[int]]] = {"points": {}, "edges": {}, "faces": {}}

    # reusable vtkIdList objects
    point_ids = _vtk.vtkIdList()  # for single-point neighbor queries
    cellIds = _vtk.vtkIdList()   # for results (will be Reset() between uses)

    for i in range(dataset.number_of_cells):
        # WARNING GetCell reuses the same output pointer
        cell = dataset.GetCell(i)  # WARNING: if the index is outside the array, it will SEGFAULT

        result["points"][i] = set()
        result["edges"][i] = set()
        result["faces"][i] = set()

        # points
        for j in [cell.point_ids.GetId(k) for k in range(cell.point_ids.GetNumberOfIds())]:
            point_ids.Reset()
            point_ids.InsertNextId(j)
            cellIds.Reset()
            dataset.GetCellNeighbors(i, point_ids, cellIds)

            result["points"][i].update(cellIds.GetId(k) for k in range(cellIds.GetNumberOfIds()))

        # edges
        for j in range(cell.GetNumberOfEdges()):
            edge_ids = cell.GetEdge(j).GetPointIds()
            cellIds.Reset()
            dataset.GetCellNeighbors(i, edge_ids, cellIds)

            result["edges"][i].update(cellIds.GetId(k) for k in range(cellIds.GetNumberOfIds()))

        # faces
        for j in range(cell.GetNumberOfFaces()):
            faceIds = cell.GetFace(j).GetPointIds()
            cellIds.Reset()
            dataset.GetCellNeighbors(i, faceIds, cellIds)

            result["faces"][i].update(cellIds.GetId(k) for k in range(cellIds.GetNumberOfIds()))

    return result
