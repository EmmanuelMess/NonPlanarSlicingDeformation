import os.path
import time

import networkx as nx
import numpy as np
import open3d as o3d  # type: ignore
import pytest
import tetgen  # type: ignore
from typing_extensions import Dict, List, Tuple, Set

from non_planar_slicing_deformation.deformer.s4_deformer import S4Functions

MODELS = "./test_models"
PI_MODEL = os.path.join(MODELS, "pi.stl")

@pytest.mark.benchmark(
    group="S4",
    min_time=0.1,
    max_time=300,
    min_rounds=100,
    timer=time.time,
    disable_gc=True,
    warmup=False
)
def testTetrahedralize(benchmark):
    """
    Test optimization for tetgen.TetGen.tetrahedralize
    """
    mesh: o3d.cpu.pybind.geometry.TriangleMesh = o3d.io.read_triangle_mesh(PI_MODEL)

    @benchmark
    def tetrahetralize():
        # convert to tetrahedral mesh
        inputTet = tetgen.TetGen(np.asarray(mesh.vertices), np.asarray(mesh.triangles))
        inputTet.tetrahedralize()


@pytest.mark.benchmark(
    group="S4",
    min_time=0.1,
    max_time=300,
    min_rounds=100,
    timer=time.time,
    disable_gc=True,
    warmup=False
)
def testCellNeighbour(benchmark):
    """
    Test optimization for S4Functions.allCellNeighbours
    """
    mesh: o3d.cpu.pybind.geometry.TriangleMesh = o3d.io.read_triangle_mesh(PI_MODEL)

    # convert to tetrahedral mesh
    inputTet = tetgen.TetGen(np.asarray(mesh.vertices), np.asarray(mesh.triangles))
    inputTet.tetrahedralize()
    inputTet = inputTet.grid

    benchmark(S4Functions.allCellNeighbours, inputTet)

@pytest.mark.benchmark(
    group="S4",
    min_time=0.1,
    max_time=300,
    min_rounds=100,
    timer=time.time,
    disable_gc=True,
    warmup=False
)
def testCalculateTetAttributes(benchmark):
    """
    Test optimization for S4Functions.calculate_tet_attributes
    """
    mesh: o3d.cpu.pybind.geometry.TriangleMesh = o3d.io.read_triangle_mesh(PI_MODEL)

    # convert to tetrahedral mesh
    inputTet = tetgen.TetGen(np.asarray(mesh.vertices), np.asarray(mesh.triangles))
    inputTet.tetrahedralize()
    inputTet = inputTet.grid

    # find neighbours
    all_neighbours: Dict[str, Dict[int, Set[int]]] = S4Functions.allCellNeighbours(inputTet)
    neighbour_type = "point"
    cell_neighbours: List[Tuple[int, int]] = []
    for cell_index in range(inputTet.number_of_cells):
        neighbours = all_neighbours[f"{neighbour_type}s"][cell_index]
        for neighbour in neighbours:
            if neighbour > cell_index:
                face_1, face_2 = cell_index, neighbour
                cell_neighbours.append((face_1, face_2))

    inputTet.field_data[f"cell_{neighbour_type}_neighbours"] = np.array(cell_neighbours)

    cell_centers = inputTet.cell_centers().points
    weightedEdges = []
    for edge in inputTet.field_data["cell_point_neighbours"]:  # use point neighbours for best accuracy
        distance = np.linalg.norm(cell_centers[edge[0]] - cell_centers[edge[1]])
        weightedEdges.append((edge[0], edge[1], distance))

    cell_neighbour_graph = nx.Graph()
    cell_neighbour_graph.add_weighted_edges_from(weightedEdges)

    benchmark(S4Functions.calculate_tet_attributes, inputTet, cell_neighbour_graph)

@pytest.mark.benchmark(
    group="S4",
    min_time=0.1,
    max_time=300,
    min_rounds=100,
    timer=time.time,
    disable_gc=True,
    warmup=True,
    warmup_iterations=2,  # for JAX
)
def testCalculateDeformation(benchmark):
    """
    Test optimization for S4Functions.calculate_deformation
    """
    neighbourLossWeight = np.float64(20)
    maxOverhang = np.float64(30)
    rotationMultiplier = np.float64(2)
    optimizeRotationIterations = np.int64(100)
    steepOverhangCompensation = True
    initialRotationFieldSmoothing = np.int64(30)
    setInitialRotationToZero = True
    maxRotation = np.float64(3600)
    minRotation = np.float64(-3600)
    calculateDeformationIterations = np.int64(50)

    mesh: o3d.cpu.pybind.geometry.TriangleMesh = o3d.io.read_triangle_mesh(PI_MODEL)

    # convert to tetrahedral mesh
    input_tet = tetgen.TetGen(np.asarray(mesh.vertices), np.asarray(mesh.triangles))
    input_tet.tetrahedralize()
    input_tet = input_tet.grid

    # find neighbours
    neighbour_types = ["point", "edge", "face"]
    cell_neighbour_dict: Dict[str, Dict[int, List[int]]] = {neighbour_type: {
        face: [] for face in range(input_tet.number_of_cells)} for neighbour_type in neighbour_types}
    all_neighbours: Dict[str, Dict[int, Set[int]]] = S4Functions.allCellNeighbours(input_tet)
    for neighbour_type in neighbour_types:
        cell_neighbours: List[Tuple[int, int]] = []
        for cell_index in range(input_tet.number_of_cells):
            neighbours = all_neighbours[f"{neighbour_type}s"][cell_index]
            for neighbour in neighbours:
                if neighbour > cell_index:
                    face_1, face_2 = cell_index, neighbour
                    cell_neighbours.append((face_1, face_2))
                    cell_neighbour_dict[neighbour_type][face_1].append(face_2)
                    cell_neighbour_dict[neighbour_type][face_2].append(face_1)

        input_tet.field_data[f"cell_{neighbour_type}_neighbours"] = np.array(cell_neighbours)

    cell_centers = input_tet.cell_centers().points
    weightedEdges = []
    for edge in input_tet.field_data["cell_point_neighbours"]:  # use point neighbours for best accuracy
        distance = np.linalg.norm(cell_centers[edge[0]] - cell_centers[edge[1]])
        weightedEdges.append((edge[0], edge[1], distance))

    cell_neighbour_graph = nx.Graph()
    cell_neighbour_graph.add_weighted_edges_from(weightedEdges)

    input_tet, bottom_cells_mask, bottom_cells = S4Functions.calculate_tet_attributes(
        input_tet, cell_neighbour_graph
    )

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

    benchmark(S4Functions.calculate_deformation, undeformed_tet, rotation_field, calculateDeformationIterations)
