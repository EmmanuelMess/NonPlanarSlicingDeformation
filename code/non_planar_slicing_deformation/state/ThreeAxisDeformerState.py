from dataclasses import dataclass

import numpy as np

from non_planar_slicing_deformation.state.DeformerState import DeformerState


@dataclass
class ThreeAxisDeformerState(DeformerState):
    """
    The state for :class:`ThreeAxisDeformer` and :class:`ThreeAxisUndeformer`
    """
    firstOrder: np.float64
    secondOrder: np.float64
    translationX: np.float64
    translationY: np.float64
