from dataclasses import dataclass

from typing_extensions import Callable, TypeVar

from non_planar_slicing_deformation.deformer.Deformer import Deformer
from non_planar_slicing_deformation.undeformer.Undeformer import Undeformer
from non_planar_slicing_deformation.ui.parameters.DeformerParameters import DeformerParameters


@dataclass
class Configuration:
    """
    Holds the deformer and undeformer classes, one should exist per element in :class:`Mode`
    """

    # TODO add a type constraint between the return of the deformer and the parameters input

    deformer: Callable[[], Deformer]
    """
    Constructor for the Deformer that will be used in the app
    """

    undeformer: Callable[[], Undeformer]
    """
    Constructor for the Undeformer that will be used in the app
    """

    defomerParameters: Callable[[Deformer], DeformerParameters]
    """
    The UI for the parameters
    """
