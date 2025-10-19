import numpy as np
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QCheckBox
from typing_extensions import Optional, cast

from non_planar_slicing_deformation.common.Conversions import forceToInt, toInt
from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.deformer.s4_deformer.S4Deformer import S4Deformer
from non_planar_slicing_deformation.ui import Strings
from non_planar_slicing_deformation.ui.parameters import UiFunctions
from non_planar_slicing_deformation.ui.parameters.deformer_parameters.DeformerParameters import DeformerParameters
from non_planar_slicing_deformation.ui.s4_windows.ViewBottomMeshWindow import ViewBottomMeshWindow
from non_planar_slicing_deformation.ui.s4_windows.ViewRotatedTrianglesWindow import ViewRotatedTrianglesWindow


class S4DeformerParameters(DeformerParameters):
    """
    UI for :class:`S4Deformer`
    """

    def __init__(self, deformer: S4Deformer, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.deformer = deformer

        self.settingsLayout = QVBoxLayout()
        self.settingsLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        offsetXSliderDefault = cast(np.float64, self.deformer.getParameters()["offset x", np.float64])
        offsetXSliderText = f"{Strings.xTranslation} ({offsetXSliderDefault / 100})"
        self.offsetXSlider, self.offsetXText = UiFunctions.labeledSlider(
            offsetXSliderText, -100, 100, np.int64(offsetXSliderDefault).item(),
            self.onOffsetXChanged
            )
        self.settingsLayout.addLayout(self.offsetXSlider)
        offsetYSliderDefault = cast(np.float64, self.deformer.getParameters()["offset y", np.float64])
        offsetYSliderText = f"{Strings.yTranslation} ({offsetYSliderDefault / 100})"
        self.offsetYSlider, self.offsetYText = UiFunctions.labeledSlider(
            offsetYSliderText, -100, 100, np.int64(offsetYSliderDefault).item(),
            self.onOffsetYChanged
            )
        self.settingsLayout.addLayout(self.offsetYSlider)
        offsetZSliderDefault = cast(np.float64, self.deformer.getParameters()["offset z", np.float64])
        offsetZSliderText = f"{Strings.zTranslation} ({offsetZSliderDefault / 100})"
        self.offsetZSlider, self.offsetZText = UiFunctions.labeledSlider(
            offsetZSliderText, -10, 10, np.int64(offsetZSliderDefault).item(),
            self.onOffsetZChanged
            )
        self.settingsLayout.addLayout(self.offsetZSlider)

        neighbourLossWeightDefault = cast(np.int64, self.deformer.getParameters()["neighbour loss weight", np.int64])
        neighbourLossWeightText = f"{Strings.neighbourLossWeight} ({neighbourLossWeightDefault})"
        self.neighbourLossWeightSlider, self.neighbourLossWeightText = UiFunctions.labeledSlider(
            neighbourLossWeightText, 0, 50, neighbourLossWeightDefault.item(),
            self.onNeighbourLossWeightChanged
            )
        self.settingsLayout.addLayout(self.neighbourLossWeightSlider)

        maxOverhangDefault = cast(np.float64, self.deformer.getParameters()["max overhang", np.float64])
        maxOverhangText = f"{Strings.maxOverhang} ({maxOverhangDefault})"
        self.maxOverhangSlider, self.maxOverhangText = UiFunctions.labeledSlider(
            maxOverhangText, 0, 100, forceToInt(maxOverhangDefault),
            self.onMaxOverhangChanged
            )
        self.settingsLayout.addLayout(self.maxOverhangSlider)

        rotationMultiplierDefault = cast(np.float64, self.deformer.getParameters()["rotation multiplier", np.float64])
        rotationMultiplierText = f"{Strings.rotationMultiplier} ({rotationMultiplierDefault})"
        self.rotationMultiplierSlider, self.rotationMultiplierText = UiFunctions.labeledSlider(
            rotationMultiplierText, 0, 10, forceToInt(rotationMultiplierDefault),
            self.onRotationMultiplierChanged
            )
        self.settingsLayout.addLayout(self.rotationMultiplierSlider)

        initialRotationToZeroDefault = cast(bool, self.deformer.getParameters()["set initial rotation to zero", bool])
        self.initialRotationToZeroCheckbox = QCheckBox(Strings.initialRotationToZero)
        self.initialRotationToZeroCheckbox.setCheckState(
            Qt.CheckState.Checked if initialRotationToZeroDefault else Qt.CheckState.Unchecked)
        self.initialRotationToZeroCheckbox.stateChanged.connect(self.onInitialRotationToZeroChanged)
        self.settingsLayout.addWidget(self.initialRotationToZeroCheckbox)

        initialRotationFieldSmoothingDefault = cast(
            np.int64, self.deformer.getParameters()[
                "initial rotation field smoothing", np.int64])
        initialRotationFieldSmoothingText = f"{
            Strings.initialRotationFieldSmoothing} ({initialRotationFieldSmoothingDefault})"
        self.initialRotationFieldSmoothingSlider, self.initialRotationFieldSmoothingText = UiFunctions.labeledSlider(
            initialRotationFieldSmoothingText, 0, 100, toInt(initialRotationFieldSmoothingDefault),
            self.onInitialRotationFieldSmoothingChanged
            )
        self.settingsLayout.addLayout(self.initialRotationFieldSmoothingSlider)

        optimizeRotationIterationsDefault = cast(
            np.int64, self.deformer.getParameters()[
                "optimize rotation iterations", np.int64])
        optimizeRotationIterationsText = f"{Strings.optimizeRotationIterations} ({optimizeRotationIterationsDefault})"
        self.optimizeRotationIterationsSlider, self.optimizeRotationIterationsText = UiFunctions.labeledSlider(
            optimizeRotationIterationsText, 0, 1000, toInt(optimizeRotationIterationsDefault),
            self.onOptimizeRotationIterationsChanged
            )
        self.settingsLayout.addLayout(self.optimizeRotationIterationsSlider)

        steepOverhangCompensationDefault = cast(
            bool, self.deformer.getParameters()[
                "steep overhang compensation", bool])
        self.steepOverhangCompensationCheckbox = QCheckBox(Strings.steepOverhangCompensation)
        self.steepOverhangCompensationCheckbox.setCheckState(
            Qt.CheckState.Checked if steepOverhangCompensationDefault else Qt.CheckState.Unchecked)
        self.steepOverhangCompensationCheckbox.stateChanged.connect(self.onSteepOverhangCompensationChanged)
        self.settingsLayout.addWidget(self.steepOverhangCompensationCheckbox)

        calculateDeformationIterationsDefault = cast(
            np.int64, self.deformer.getParameters()[
                "calculate deformation iterations", np.int64])
        calculateDeformationIterationsText = f"{
            Strings.calculateDeformationIterations} ({calculateDeformationIterationsDefault})"
        self.calculateDeformationIterationsSlider, self.calculateDeformationIterationsText = UiFunctions.labeledSlider(
            calculateDeformationIterationsText, 0, 1000, toInt(calculateDeformationIterationsDefault),
            self.onCalculateDeformationIterationsChanged
            )
        self.settingsLayout.addLayout(self.calculateDeformationIterationsSlider)

        self.applyParametersButton = QPushButton(Strings.applyParameters)
        self.applyParametersButton.pressed.connect(self.parameterUpdate)
        self.settingsLayout.addWidget(self.applyParametersButton)

        self.viewRotatedTrianglesButton = QPushButton(Strings.viewRotatedTriangles)
        self.viewRotatedTrianglesButton.pressed.connect(self.onViewRotatedTriangles)
        self.settingsLayout.addWidget(self.viewRotatedTrianglesButton)

        self.viewBottomMeshButton = QPushButton(Strings.viewBottomMesh)
        self.viewBottomMeshButton.pressed.connect(self.onViewBottomMesh)
        self.settingsLayout.addWidget(self.viewBottomMeshButton)

        self.setLayout(self.settingsLayout)

    @Slot(int)
    def onOffsetXChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["offset x"] = np.float64(value) / 100

        self.offsetXText.setText(f"{Strings.xTranslation} ({np.float64(value) / 100})")

    @Slot(int)
    def onOffsetYChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["offset y"] = np.float64(value) / 100

        self.offsetYText.setText(f"{Strings.yTranslation} ({np.float64(value) / 100})")

    @Slot(int)
    def onOffsetZChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["offset z"] = np.float64(value) / 100

        self.offsetZText.setText(f"{Strings.zTranslation} ({np.float64(value) / 100})")

    @Slot(int)
    def onNeighbourLossWeightChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["neighbour loss weight"] = np.int64(value)

        self.neighbourLossWeightText.setText(f"{Strings.neighbourLossWeight} ({np.int64(value)})")

    @Slot(int)
    def onMaxOverhangChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["max overhang"] = np.float64(value)

        self.maxOverhangText.setText(f"{Strings.maxOverhang} ({np.float64(value)})")

    @Slot(int)
    def onRotationMultiplierChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["rotation multiplier"] = np.float64(value)

        self.rotationMultiplierText.setText(f"{Strings.rotationMultiplier} ({np.float64(value)})")

    @Slot(Qt.CheckState)
    def onInitialRotationToZeroChanged(self, value: Qt.CheckState) \
            -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["set initial rotation to zero"] = value == Qt.CheckState.Checked.value

    @Slot(int)
    def onInitialRotationFieldSmoothingChanged(self, value: int)\
            -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["initial rotation field smoothing"] = np.int64(value)

        self.initialRotationFieldSmoothingText.setText(f"{Strings.initialRotationFieldSmoothing} ({np.int64(value)})")

    @Slot(int)
    def onOptimizeRotationIterationsChanged(self, value: int) -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["optimize rotation iterations"] = np.int64(value)

        self.optimizeRotationIterationsText.setText(f"{Strings.optimizeRotationIterations} ({np.int64(value)})")

    @Slot(Qt.CheckState)
    def onSteepOverhangCompensationChanged(self, value: Qt.CheckState)\
            -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["steep overhang compensation"] = value == Qt.CheckState.Checked.value

    @Slot(int)
    def onCalculateDeformationIterationsChanged(self, value: int) \
            -> None:  # pylint: disable=missing-function-docstring
        self.deformer.getParameters()["calculate deformation iterations"] = np.int64(value)

        self.calculateDeformationIterationsText.setText(f"{Strings.calculateDeformationIterations} ({np.int64(value)})")

    @Slot()
    def onViewRotatedTriangles(self) -> None:
        rotatedTriangles = self.deformer.getRotatedTriangles()
        if rotatedTriangles is None:
            MAIN_LOGGER.error("deformer.getRotatedTriangles() is None, did you forget to call deform()?")
            return

        self.rotatedTrianglesWindow = ViewRotatedTrianglesWindow(rotatedTriangles)
        self.rotatedTrianglesWindow.show()

    @Slot()
    def onViewBottomMesh(self) -> None:
        bottomMesh = self.deformer.getBottomMesh()
        if bottomMesh is None:
            MAIN_LOGGER.error("deformer.getBottomMesh() is None, did you forget to call deform()?")
            return

        self.bottomMeshWindow = ViewBottomMeshWindow(bottomMesh)
        self.bottomMeshWindow.show()
