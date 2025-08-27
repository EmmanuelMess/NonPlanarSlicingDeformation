import numpy as np
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QLabel, QWidget, QSlider, QVBoxLayout
from typing_extensions import Optional, Callable

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

        zerothOrderSliderDefault = np.int64(self.deformer.getParameters()["zeroth order", np.float64] * 100).item()
        self.zerothOrderSlider = self._labeledSlider(Strings.zerothOrderSlider, -100, 100,
                                                     zerothOrderSliderDefault, self.onZerothOrderChanged)
        self.settingsLayout.addLayout(self.zerothOrderSlider)
        firstOrderSliderDefault = np.int64(self.deformer.getParameters()["first order", np.float64] * 100).item()
        self.firstOrderSlider = self._labeledSlider(Strings.firstOrderSlider, -100, 100, firstOrderSliderDefault,
                                                    self.onFirstOrderChanged)
        self.settingsLayout.addLayout(self.firstOrderSlider)
        secondOrderSliderDefault = np.int64(self.deformer.getParameters()["second order", np.float64] * 100).item()
        self.secondOrderSlider = self._labeledSlider(Strings.secondOrderSlider, -10, 10,
                                                     secondOrderSliderDefault, self.onSecondOrderChanged)
        self.settingsLayout.addLayout(self.secondOrderSlider)

        startSliderDefault = np.int64(self.deformer.getParameters()["start", np.float64] * 100).item()
        self.startSlider = self._labeledSlider(Strings.startSlider, 0, 10000, startSliderDefault,
                                               self.onStartChanged)
        self.settingsLayout.addLayout(self.startSlider)
        endSliderDefault = np.int64(self.deformer.getParameters()["end", np.float64] * 100).item()
        self.endSlider = self._labeledSlider(Strings.endSlider, 0, 10000, endSliderDefault,
                                             self.onEndChanged)
        self.settingsLayout.addLayout(self.endSlider)

        self.setLayout(self.settingsLayout)

    def _labeledSlider(self, text: str, minv: int, maxv: int, default: int, slot: Callable[[int], None]) \
            -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel()
        label.setText(text)
        layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setRange(minv, maxv)
        slider.setValue(default)
        slider.valueChanged.connect(slot)
        layout.addWidget(slider)

        return layout

    @Slot(int)
    def onZerothOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["zeroth order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onFirstOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["first order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onSecondOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["second order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onStartChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["start"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onEndChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["end"] = np.float64(value) / 100
        self.parameterUpdate.emit()
