from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.deformer.Deformer import Deformer
from non_planar_slicing_deformation.deformer.worker.SimpleDeformerWorker import SimpleDeformerWorker


class SimpleDeformer(Deformer):
    def __init__(self) -> None:
        super().__init__(Defaults.simpleDeformerDefaults, SimpleDeformerWorker())
