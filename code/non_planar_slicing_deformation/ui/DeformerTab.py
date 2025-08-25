import pyvista as pv
import pyvistaqt as pvqt  # type: ignore
from PySide6.QtCore import Slot, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFileDialog, QPushButton, QHBoxLayout, QSlider, QLabel
from typing_extensions import Optional, cast

from non_planar_slicing_deformation.common import Constants
from non_planar_slicing_deformation.common.MainLoggerHolder import MAIN_LOGGER
from non_planar_slicing_deformation.configuration.Configuration import Configuration
from non_planar_slicing_deformation.deformer.Deformer import Deformer
from non_planar_slicing_deformation.ui import Strings


class DeformerTab(QWidget):  # pylint: disable=duplicate-code
    """
    QWidget that draws the deformer view
    """

    def __init__(self, configuration: Configuration, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # State
        self.deformer: Deformer = configuration.deformer()

        # Layout
        self.rootLayout = QHBoxLayout()
        self.centralLayout = QVBoxLayout()
        self.plottersLayout = QHBoxLayout()
        self.buttonLayout = QHBoxLayout()

        # TODO add controls tutorial
        # TODO link both plotters's cameras
        self.plotterLeft = pvqt.QtInteractor()
        self.plottersLayout.addWidget(self.plotterLeft)
        self.plotterRight = pvqt.QtInteractor()
        self.plottersLayout.addWidget(self.plotterRight)

        self.centralLayout.addLayout(self.plottersLayout)
        self.centralLayout.addLayout(self.buttonLayout)

        self.inputModelButton = QPushButton(Strings.openModel)
        self.inputModelButton.clicked.connect(self.onSelectInputFile)
        self.buttonLayout.addWidget(self.inputModelButton)

        self.outputModelButton = QPushButton(Strings.saveModel)
        self.outputModelButton.clicked.connect(self.onSelectOutputFile)
        self.buttonLayout.addWidget(self.outputModelButton)

        self.deformerParameters = configuration.defomerParameters(self.deformer)
        self.deformerParameters.setFixedWidth(Constants.widthSettings)
        self.deformerParameters.update.connect(self.onParameterUpdated)

        self.rootLayout.addLayout(self.centralLayout)
        self.rootLayout.addWidget(self.deformerParameters)

        self.setLayout(self.rootLayout)

        self.inputFileDialog = QFileDialog(self)
        self.inputFileDialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.inputFileDialog.setWindowTitle(Strings.openModel)
        self.inputFileDialog.setMimeTypeFilters(["model/stl"])
        self.inputFileDialog.fileSelected.connect(self.onSelectedInputFile)

        self.outputFileDialog = QFileDialog(self)
        self.outputFileDialog.setFileMode(QFileDialog.FileMode.AnyFile)
        self.outputFileDialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        self.outputFileDialog.setWindowTitle(Strings.saveModel)
        self.outputFileDialog.fileSelected.connect(self.onSelectedOutputFile)

    @Slot()
    def onParameterUpdated(self) -> None:  # pylint: disable=missing-function-docstring
        self._updateDeformedMesh()

    @Slot()
    def onSelectInputFile(self) -> None:  # pylint: disable=missing-function-docstring
        self.inputFileDialog.open()

    @Slot()
    def onSelectedInputFile(self, path: str) -> None:  # pylint: disable=missing-function-docstring
        if self.deformer is None:
            MAIN_LOGGER.error("Deformer is None, did you forget to call setConfiguration?")
            return

        if len(path) == 0:
            MAIN_LOGGER.error("No models selected!")
            return

        loadedMesh: pv.DataObject = pv.read(path)

        if not isinstance(loadedMesh, pv.DataSet):
            MAIN_LOGGER.warning("Model is not a pv.DataSet!")
            return

        self.plotterLeft.clear_actors()
        self.plotterLeft.add_mesh(loadedMesh)

        self.deformer.setMesh(cast(pv.DataSet, loadedMesh))
        self._updateDeformedMesh()

    @Slot()
    def onSelectOutputFile(self) -> None:  # pylint: disable=missing-function-docstring
        self.outputFileDialog.open()

    @Slot()
    def onSelectedOutputFile(self, path: str) -> None:  # pylint: disable=missing-function-docstring
        if self.deformer is None:
            MAIN_LOGGER.error("Deformer is None, did you forget to call setConfiguration?")
            return

        if len(path) == 0:
            MAIN_LOGGER.error("No path chosen!")
            return

        self.deformer.save(path)

    def _updateDeformedMesh(self) -> None:
        if self.deformer is None:
            MAIN_LOGGER.error("Deformer is None, did you forget to call setConfiguration?")
            return

        self.deformer.deform()
        deformedMesh: Optional[pv.DataSet] = self.deformer.getDeformedMesh()

        if deformedMesh is not None:
            self.plotterRight.clear_actors()
            self.plotterRight.add_mesh(deformedMesh)
        else:
            MAIN_LOGGER.error("Deformed mesh cannot be shown!")
