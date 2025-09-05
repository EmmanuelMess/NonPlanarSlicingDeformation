import numpy as np
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QLabel, QWidget, QSlider, QVBoxLayout
from typing_extensions import Optional, Callable, cast, Tuple

from non_planar_slicing_deformation.deformer.SimpleDeformer import SimpleDeformer
from non_planar_slicing_deformation.ui import Strings
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
        self.zerothOrderSlider, self.zerothOrderText = self._labeledSlider(
            Strings.zerothOrderSlider, -100, 100, np.int64(zerothOrderSliderDefault * 100).item(),
            self.onZerothOrderChanged
            )
        self.settingsLayout.addLayout(self.zerothOrderSlider)
        firstOrderSliderDefault = cast(np.float64, self.deformer.getParameters()["first order", np.float64])
        self.firstOrderSlider, self.firstOrderText = self._labeledSlider(
            Strings.firstOrderSlider, -100, 100, np.int64(firstOrderSliderDefault * 100).item(),
            self.onFirstOrderChanged
            )
        self.settingsLayout.addLayout(self.firstOrderSlider)
        secondOrderSliderDefault = cast(np.float64, self.deformer.getParameters()["second order", np.float64])
        self.secondOrderSlider, self.secondOrderText = self._labeledSlider(
            Strings.secondOrderSlider, -10, 10, np.int64(secondOrderSliderDefault * 100).item(),
            self.onSecondOrderChanged
            )
        self.settingsLayout.addLayout(self.secondOrderSlider)

        self.setLayout(self.settingsLayout)

    def _labeledSlider(self, text: str, minv: int, maxv: int, default: int, slot: Callable[[int], None]) \
            -> Tuple[QVBoxLayout, QLabel]:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel()
        label.setText(f"{text} ({default / 100})")
        layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setRange(minv, maxv)
        slider.setValue(default)
        slider.valueChanged.connect(slot)
        layout.addWidget(slider)

        return layout, label

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
