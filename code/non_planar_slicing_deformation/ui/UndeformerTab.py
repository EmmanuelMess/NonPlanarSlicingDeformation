import pyvistaqt as pvqt  # type: ignore
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog
from typing_extensions import Optional, List

from non_planar_slicing_deformation.common import Constants
from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.Configuration import Configuration
from non_planar_slicing_deformation.ui import Strings, GcodePlotHelper
from non_planar_slicing_deformation.undeformer.Undeformer import Undeformer


class UndeformerTab(QWidget):  # pylint: disable=duplicate-code
    """
    QWidget that draws the undeformer view
    """

    def __init__(self, configuration: Configuration, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.undeformer: Undeformer = configuration.undeformer()

        # Layout
        self.rootLayout = QHBoxLayout(self)
        self.centralLayout = QVBoxLayout(self)
        self.plottersLayout = QHBoxLayout(self)
        self.buttonLayout = QHBoxLayout(self)

        # TODO add controls tutorial
        # TODO link both plotters's cameras
        self.plotterLeft = pvqt.QtInteractor()
        self.plottersLayout.addWidget(self.plotterLeft)
        self.plotterRight = pvqt.QtInteractor()
        self.plottersLayout.addWidget(self.plotterRight)

        self.centralLayout.addLayout(self.plottersLayout)
        self.centralLayout.addLayout(self.buttonLayout)

        self.inputModelButton = QPushButton(Strings.openGcode)
        self.inputModelButton.clicked.connect(self.onSelectInputFile)
        self.buttonLayout.addWidget(self.inputModelButton)

        self.outputModelButton = QPushButton(Strings.saveGcode)
        self.outputModelButton.clicked.connect(self.onSelectOutputFile)
        self.buttonLayout.addWidget(self.outputModelButton)

        self.undeformerParameters = configuration.undeformerParameters(self.undeformer)
        self.undeformerParameters.setFixedWidth(Constants.widthSettings)
        self.undeformerParameters.parameterUpdate.connect(self.onParameterUpdated)

        self.rootLayout.addLayout(self.centralLayout)
        self.rootLayout.addWidget(self.undeformerParameters)

        self.inputFileDialog = QFileDialog(self)
        self.inputFileDialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.inputFileDialog.setWindowTitle(Strings.openModel)
        self.inputFileDialog.setMimeTypeFilters(["application/x-gcode"])
        self.inputFileDialog.fileSelected.connect(self.onSelectedInputFile)

        self.outputFileDialog = QFileDialog(self)
        self.outputFileDialog.setFileMode(QFileDialog.FileMode.AnyFile)
        self.outputFileDialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.outputFileDialog.setWindowTitle(Strings.saveModel)
        self.outputFileDialog.fileSelected.connect(self.onSelectedOutputFile)

    @Slot()
    def onSelectInputFile(self) -> None:  # pylint: disable=missing-function-docstring
        self.inputFileDialog.open()

    @Slot()
    def onSelectedInputFile(self, path: str) -> None:  # pylint: disable=missing-function-docstring
        if self.undeformer is None:
            MAIN_LOGGER.error("Undeformer is None, did you forget to call setConfiguration?")
            return

        if len(path) == 0:
            MAIN_LOGGER.error("No models selected!")
            return

        gcode: Optional[List[str]] = None

        with open(path, "rt", encoding="utf-8") as gcodeFile:
            gcode = gcodeFile.readlines()

        if gcode is None:
            MAIN_LOGGER.warning("Gcode did not load")
            return

        mesh, colorMap = GcodePlotHelper.plottable3AxisGcode(gcode)

        self.plotterLeft.clear_actors()
        self.plotterLeft.add_mesh(mesh, scalars=colorMap, cmap="prism")

        self.undeformer.setGcode(gcode)
        self._updateUndeformedMesh()

    @Slot()
    def onSelectOutputFile(self) -> None:  # pylint: disable=missing-function-docstring
        self.outputFileDialog.open()

    @Slot()
    def onSelectedOutputFile(self, path: str) -> None:  # pylint: disable=missing-function-docstring
        if self.undeformer is None:
            MAIN_LOGGER.error("Undeformer is None, did you forget to call setConfiguration?")
            return

        if len(path) == 0:
            MAIN_LOGGER.error("No path chosen!")
            return

        self.undeformer.save(path)

    def _updateUndeformedMesh(self) -> None:
        if self.undeformer is None:
            MAIN_LOGGER.error("Undeformer is None, did you forget to call setConfiguration?")
            return

        self.undeformer.undeform()
        undeformedGcode: Optional[List[str]] = self.undeformer.getUndeformedGcode()

        if undeformedGcode is not None:
            mesh, colorMap = GcodePlotHelper.plottable4AxisGcode(undeformedGcode)

            self.plotterRight.clear_actors()
            self.plotterRight.show_grid()
            self.plotterRight.add_mesh(mesh, scalars=colorMap, cmap="prism")
        else:
            MAIN_LOGGER.error("Undeformed mesh cannot be shown!")

    @Slot()
    def onParameterUpdated(self) -> None:  # pylint: disable=missing-function-docstring
        if self.undeformer is None:
            MAIN_LOGGER.error("Undeformer is None, did you forget to call setConfiguration?")
            return

        # Rerun the complete undeformer
        self.undeformer.undeform()
