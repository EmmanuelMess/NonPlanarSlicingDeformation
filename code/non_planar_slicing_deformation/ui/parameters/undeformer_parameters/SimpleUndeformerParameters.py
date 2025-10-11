from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from typing_extensions import Optional, cast

from non_planar_slicing_deformation.ui.parameters.undeformer_parameters.UndeformerParameters import UndeformerParameters
from non_planar_slicing_deformation.undeformer.SimpleUndeformer import SimpleUndeformer
from non_planar_slicing_deformation.ui import Strings
from non_planar_slicing_deformation.ui.parameters import UiFunctions


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

        heatUpExtruderCheckBoxDefault = cast(bool, self.undeformer.getParameters()["heat extruder", bool])

        self.heatUpExtruderCheckbox = QCheckBox(Strings.heatUpExtruder)
        self.heatUpExtruderCheckbox.setCheckState(
            Qt.CheckState.Checked if heatUpExtruderCheckBoxDefault else Qt.CheckState.Unchecked)
        self.heatUpExtruderCheckbox.stateChanged.connect(self.onHeatUpExtruderChanged)
        self.settingsLayout.addWidget(self.heatUpExtruderCheckbox)

        temperatureSliderDefault = cast(int, self.undeformer.getParameters()["heat extruder temperature", int])
        temperatureSliderText = f"{Strings.temperatureSlider} ({temperatureSliderDefault}°C)"
        self.temperatureSlider, self.temperatureText = UiFunctions.labeledSlider(
            temperatureSliderText, 190, 250, temperatureSliderDefault, self.onTemperatureChanged)
        self.settingsLayout.addLayout(self.temperatureSlider)

        self.setLayout(self.settingsLayout)

    @Slot(Qt.CheckState)
    def onHomeAllChanged(self, value: Qt.CheckState) -> None:  # pylint: disable=missing-function-docstring
        self.undeformer.getParameters()["home all"] = value == Qt.CheckState.Checked.value
        self.parameterUpdate.emit()

    @Slot(Qt.CheckState)
    def onHeatUpExtruderChanged(self, value: Qt.CheckState) -> None:  # pylint: disable=missing-function-docstring
        self.undeformer.getParameters()["heat extruder"] = value == Qt.CheckState.Checked.value
        self.parameterUpdate.emit()

    @Slot(float)
    def onTemperatureChanged(self, value: float) -> None:  # pylint: disable=missing-function-docstring
        self.undeformer.getParameters()["heat extruder temperature"] = value
        self.parameterUpdate.emit()

        self.temperatureText.setText(f"{Strings.temperatureSlider} ({value}°C)")
