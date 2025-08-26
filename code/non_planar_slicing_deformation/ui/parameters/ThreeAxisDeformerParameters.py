import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider
from typing_extensions import Optional, Callable

from non_planar_slicing_deformation.deformer.ThreeAxisDeformer import ThreeAxisDeformer
from non_planar_slicing_deformation.ui import Strings
from non_planar_slicing_deformation.ui.parameters.DeformerParameters import DeformerParameters


class ThreeAxisDeformerParameters(DeformerParameters):

    def __init__(self, deformer: ThreeAxisDeformer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.deformer = deformer

        self.settingsLayout = QVBoxLayout()
        self.settingsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.firstOrderSlider = self._labeledSlider(Strings.firstOrderSlider, -100, 100, self.onFirstOrderChanged)
        self.settingsLayout.addLayout(self.firstOrderSlider)
        self.secondOrderSlider = self._labeledSlider(Strings.secondOrderSlider, -10, 10, self.onSecondOrderChanged)
        self.settingsLayout.addLayout(self.secondOrderSlider)

        self.xTranslationSlider = self._labeledSlider(Strings.xTranslation, -100, 100, self.onXTranslationChanged)
        self.settingsLayout.addLayout(self.xTranslationSlider)
        self.yTranslationSlider = self._labeledSlider(Strings.yTranslation, -100, 100, self.onYTranslationChanged)
        self.settingsLayout.addLayout(self.yTranslationSlider)

        self.setLayout(self.settingsLayout)

    def _labeledSlider(self, text: str, minv: int, maxv: int, slot: Callable[[int], None]) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        label = QLabel()
        label.setText(text)
        layout.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setRange(minv, maxv)
        slider.valueChanged.connect(slot)
        layout.addWidget(slider)

        return layout

    @Slot(int)
    def onFirstOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["first order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onSecondOrderChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["second order"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onXTranslationChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["x translation"] = np.float64(value) / 100
        self.parameterUpdate.emit()

    @Slot(int)
    def onYTranslationChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["y translation"] = np.float64(value) / 100
        self.parameterUpdate.emit()
