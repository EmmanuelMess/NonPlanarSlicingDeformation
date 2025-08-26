import sys

from PySide6 import QtWidgets
from PySide6.QtCore import Slot
from typing_extensions import Dict, cast

from non_planar_slicing_deformation.deformer.ThreeAxisDeformer import ThreeAxisDeformer
from non_planar_slicing_deformation.common.Singleton import Singleton
from non_planar_slicing_deformation.configuration.Configuration import Configuration
from non_planar_slicing_deformation.deformer.SimpleDeformer import SimpleDeformer
from non_planar_slicing_deformation.ui.MainWindow import MainWindow
from non_planar_slicing_deformation.ui.Mode import Mode
from non_planar_slicing_deformation.ui.ModeSelectorWindow import ModeSelectorWindow
from non_planar_slicing_deformation.undeformer.SimpleUndeformer import SimpleUndeformer
from non_planar_slicing_deformation.ui.LogsWindow import LogsWindow
from non_planar_slicing_deformation.undeformer.ThreeAxisUndeformer import ThreeAxisUndeformer
from non_planar_slicing_deformation.ui.parameters.SimpleDeformerParameters import SimpleDeformerParameters
from non_planar_slicing_deformation.ui.parameters.ThreeAxisDeformerParameters import ThreeAxisDeformerParameters


class MainApp(metaclass=Singleton):
    """
    Initial runner for the app, container for the state of the main Qt runner, and the main window
    """

    _CONFIGURATION: Dict[Mode, Configuration] = {
        Mode.FOUR_AXIS_SIMPLE: Configuration(
            deformer=SimpleDeformer, undeformer=SimpleUndeformer,
            defomerParameters=lambda deformer: SimpleDeformerParameters(cast(SimpleDeformer, deformer))
            ),
        # Mode.FOUR_S: None,
        Mode.THREE_AXIS: Configuration(
            deformer=ThreeAxisDeformer, undeformer=ThreeAxisUndeformer,
            defomerParameters=lambda deformer: ThreeAxisDeformerParameters(cast(ThreeAxisDeformer, deformer))
            ),
        }

    def __init__(self) -> None:
        super().__init__()
        self.app = QtWidgets.QApplication([])

        self.selectorWindow = ModeSelectorWindow()
        self.selectorWindow.showLogs.connect(self.onShowLogs)
        self.selectorWindow.accepted.connect(self.onAccepted)

    def run(self) -> None:
        """
        Runs the app
        """

        self.selectorWindow.show()
        sys.exit(self.app.exec())

    @Slot(Mode)
    def onAccepted(self, mode: Mode) -> None:  # pylint: disable=missing-function-docstring
        self.mainWindow = MainWindow(self._CONFIGURATION[mode])
        self.mainWindow.showLogs.connect(self.onShowLogs)
        self.mainWindow.show()

    @Slot()
    def onShowLogs(self) -> None:  # pylint: disable=missing-function-docstring
        self.logsWindow = LogsWindow()
        self.logsWindow.show()
