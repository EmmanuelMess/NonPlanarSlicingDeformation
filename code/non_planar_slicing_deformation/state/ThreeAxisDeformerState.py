from dataclasses import dataclass

import numpy as np
from typing_extensions import Callable

from non_planar_slicing_deformation.state.DeformerState import DeformerState


@dataclass
class ThreeAxisDeformerState(DeformerState):
    """
    The state for :class:`ThreeAxisDeformer` and :class:`ThreeAxisUndeformer`
    """
    firstOrder: float
    secondOrder: float
    translationX: float
    translationY: float
