from dataclasses import dataclass

import networkx as nx
import pyvista as pv

from non_planar_slicing_deformation.state.DeformerState import DeformerState


@dataclass
class S4DeformerState(DeformerState):
    """
    The state for :class:`S4Deformer` and :class:`S4Undeformer`
    """

    input_tet: pv.UnstructuredGrid
    deformed_tet: pv.UnstructuredGrid
    cell_neighbour_graph: nx.Graph
