from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from typing_extensions import Optional

from non_planar_slicing_deformation.ui.parameters.undeformer_parameters.UndeformerParameters import UndeformerParameters
from non_planar_slicing_deformation.undeformer.ThreeAxisUndeformer import ThreeAxisUndeformer


class ThreeAxisUndeformerParameters(UndeformerParameters):

    def __init__(self, undeformer: ThreeAxisUndeformer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.undeformer = undeformer

        self.settingsLayout = QVBoxLayout()
        self.settingsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Nothing

        self.setLayout(self.settingsLayout)
