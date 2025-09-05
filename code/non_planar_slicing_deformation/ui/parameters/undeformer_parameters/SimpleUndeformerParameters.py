from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from typing_extensions import Optional, cast

from non_planar_slicing_deformation.ui.parameters.undeformer_parameters.UndeformerParameters import UndeformerParameters
from non_planar_slicing_deformation.undeformer.SimpleUndeformer import SimpleUndeformer
from non_planar_slicing_deformation.ui import Strings


class SimpleUndeformerParameters(UndeformerParameters):
    """
    UI for :class:`SimpleUndeformer`
    """

    def __init__(self, undeformer: SimpleUndeformer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.undeformer = undeformer

        self.settingsLayout = QVBoxLayout()
        self.settingsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        homeAllCheckBoxDefault = cast(bool, self.undeformer.getParameters()["home all", bool])

        self.homeAllCheckbox = QCheckBox(Strings.homeAll)
        self.homeAllCheckbox.setCheckState(Qt.CheckState.Checked if homeAllCheckBoxDefault else Qt.CheckState.Unchecked)
        self.homeAllCheckbox.stateChanged.connect(self.onHomeAllChanged)

        self.settingsLayout.addWidget(self.homeAllCheckbox)

        self.setLayout(self.settingsLayout)

    @Slot(int)
    def onHomeAllChanged(self, value: Qt.CheckState) -> None:  # pylint: disable=missing-function-docstring
        self.undeformer.getParameters()["home all"] = value == Qt.CheckState.Checked.value
        self.parameterUpdate.emit()
