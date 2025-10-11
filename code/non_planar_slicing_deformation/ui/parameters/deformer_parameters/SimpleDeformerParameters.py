import numpy as np
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from typing_extensions import Optional, cast

from non_planar_slicing_deformation.deformer.SimpleDeformer import SimpleDeformer
from non_planar_slicing_deformation.ui import Strings
from non_planar_slicing_deformation.ui.parameters import UiFunctions
from non_planar_slicing_deformation.ui.parameters.deformer_parameters.DeformerParameters import DeformerParameters


class SimpleDeformerParameters(DeformerParameters):
    """
    UI for :class:`SimpleDeformer`
    """

    def __init__(self, deformer: SimpleDeformer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.deformer = deformer

        self.settingsLayout = QVBoxLayout()
        self.settingsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        zerothOrderSliderDefault = cast(np.float64, self.deformer.getParameters()["zeroth order", np.float64])
        self.zerothOrderSlider, self.zerothOrderText = UiFunctions.labeledSlider(
            f"{Strings.zerothOrderSlider} ({zerothOrderSliderDefault / 100})", -100, 100, np.int64(zerothOrderSliderDefault * 100).item(),
            self.onZerothOrderChanged
            )
        self.settingsLayout.addLayout(self.zerothOrderSlider)
        firstOrderSliderDefault = cast(np.float64, self.deformer.getParameters()["first order", np.float64])
        self.firstOrderSlider, self.firstOrderText = UiFunctions.labeledSlider(
            f"{Strings.firstOrderSlider} ({firstOrderSliderDefault / 100})", -100, 100, np.int64(firstOrderSliderDefault * 100).item(),
            self.onFirstOrderChanged
            )
        self.settingsLayout.addLayout(self.firstOrderSlider)
        secondOrderSliderDefault = cast(np.float64, self.deformer.getParameters()["second order", np.float64])
        self.secondOrderSlider, self.secondOrderText = UiFunctions.labeledSlider(
            f"{Strings.secondOrderSlider} ({secondOrderSliderDefault / 100})", -10, 10, np.int64(secondOrderSliderDefault * 100).item(),
            self.onSecondOrderChanged
            )
        self.settingsLayout.addLayout(self.secondOrderSlider)

        self.setLayout(self.settingsLayout)

    @Slot(int)
    def onZerothOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["zeroth order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

        self.zerothOrderText.setText(f"{Strings.zerothOrderSlider} ({np.float64(value) / 100})")

    @Slot(int)
    def onFirstOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["first order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

        self.firstOrderText.setText(f"{Strings.firstOrderSlider} ({np.float64(value) / 100})")

    @Slot(int)
    def onSecondOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["second order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

        self.secondOrderText.setText(f"{Strings.secondOrderSlider} ({np.float64(value) / 100})")
