from non_planar_slicing_deformation.configuration import Defaults
from non_planar_slicing_deformation.undeformer.Undeformer import Undeformer
from non_planar_slicing_deformation.undeformer.worker.S4UndeformerWorker import S4UndeformerWorker


class S4Undeformer(Undeformer):

    def __init__(self) -> None:
        super().__init__(Defaults.s4UndeformerDefaults, S4UndeformerWorker())
