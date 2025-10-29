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
        inputTet.make_manifold()  # Try worst case (with make_manifold) always
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
    inputTet.make_manifold()  # Try worst case (with make_manifold) always
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
    inputTet.make_manifold()  # Try worst case (with make_manifold) always
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