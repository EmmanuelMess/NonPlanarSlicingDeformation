from typing_extensions import Optional

from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.state.SimpleDeformerState import SimpleDeformerState
from non_planar_slicing_deformation.undeformer.Undeformer import Undeformer
from non_planar_slicing_deformation.undeformer.worker.SimpleUndeformerWorker import SimpleUndeformerWorker


class SimpleUndeformer(Undeformer):
    """
    Simple undefomer, original implementation by Joshua Bird at https://github.com/jyjblrd/Radial_Non_Planar_Slicer.
    """

    def __init__(self) -> None:
        super().__init__(Defaults.simpleUndeformerDefaults, SimpleUndeformerWorker())

        self.state: Optional[SimpleDeformerState] = None
