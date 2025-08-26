from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QLabel, QWidget, QSlider, QVBoxLayout
from typing_extensions import Optional

from non_planar_slicing_deformation.deformer.SimpleDeformer import SimpleDeformer
from non_planar_slicing_deformation.ui import Strings
from non_planar_slicing_deformation.ui.parameters.DeformerParameters import DeformerParameters


class SimpleDeformerParameters(DeformerParameters):
    """
    UI for :class:`SimpleDeformer`
    """

    def __init__(self, deformer: SimpleDeformer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.deformer = deformer

        self.settingsLayout = QVBoxLayout()
        self.settingsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.textRadius = QLabel()
        self.textRadius.setText(Strings.deformationFactor)
        self.settingsLayout.addWidget(self.textRadius)

        self.radiusSlider = QSlider(Qt.Orientation.Horizontal)
        self.radiusSlider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.radiusSlider.setRange(-314, 314)
        self.radiusSlider.valueChanged.connect(self.onRadiusChanged)
        self.settingsLayout.addWidget(self.radiusSlider)

        self.setLayout(self.settingsLayout)

    @Slot()
    def onRadiusChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["radius"] = float(value) / 100
        self.parameterUpdate.emit()
