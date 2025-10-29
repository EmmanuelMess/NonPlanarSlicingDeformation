import time

import numpy as np
import open3d as o3d  # type: ignore
import pytest
import tetgen  # type: ignore

from non_planar_slicing_deformation.deformer.s4_deformer import S4Functions

MODELS = "test_models"

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
    Test optimization for cell_neighbours_optimized
    """
    modelPath = f"{MODELS}/pi.stl"
    mesh: o3d.cpu.pybind.geometry.TriangleMesh = o3d.io.read_triangle_mesh(modelPath)

    # convert to tetrahedral mesh
    inputTet = tetgen.TetGen(np.asarray(mesh.vertices), np.asarray(mesh.triangles))
    # input_tet.make_manifold() # comment out if not needed
    inputTet.tetrahedralize()
    inputTet = inputTet.grid

    benchmark(S4Functions.allCellNeighbours, inputTet)
