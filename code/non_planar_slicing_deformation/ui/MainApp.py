import sys

from PySide6 import QtWidgets
from PySide6.QtCore import Slot
from typing_extensions import Dict, cast

from non_planar_slicing_deformation.deformer.s4_deformer.S4Deformer import S4Deformer
from non_planar_slicing_deformation.common.Singleton import Singleton
from non_planar_slicing_deformation.configuration.Configuration import Configuration
from non_planar_slicing_deformation.deformer.SimpleDeformer import SimpleDeformer
from non_planar_slicing_deformation.ui.MainWindow import MainWindow
from non_planar_slicing_deformation.ui.Mode import Mode
from non_planar_slicing_deformation.ui.ModeSelectorWindow import ModeSelectorWindow
from non_planar_slicing_deformation.undeformer.SimpleUndeformer import SimpleUndeformer
from non_planar_slicing_deformation.undeformer.s4_undeformer.S4Undeformer import S4Undeformer
from non_planar_slicing_deformation.ui.LogsWindow import LogsWindow
from non_planar_slicing_deformation.ui.parameters.deformer_parameters.SimpleDeformerParameters\
    import SimpleDeformerParameters
from non_planar_slicing_deformation.ui.parameters.deformer_parameters.S4DeformerParameters import S4DeformerParameters
from non_planar_slicing_deformation.ui.parameters.undeformer_parameters.SimpleUndeformerParameters\
    import SimpleUndeformerParameters
from non_planar_slicing_deformation.ui.parameters.undeformer_parameters.S4UndeformerParameters\
    import S4UndeformerParameters


class MainApp(metaclass=Singleton):
    """
    Initial runner for the app, container for the state of the main Qt runner, and the main window
    """

    _CONFIGURATION: Dict[Mode, Configuration] = {
        Mode.FOUR_AXIS_SIMPLE: Configuration(
            deformer=SimpleDeformer, undeformer=SimpleUndeformer,
            defomerParameters=lambda deformer: SimpleDeformerParameters(cast(SimpleDeformer, deformer)),
            undeformerParameters=lambda undeformer: SimpleUndeformerParameters(cast(SimpleUndeformer, undeformer))
            ),
        Mode.FOUR_S: Configuration(
            deformer=S4Deformer, undeformer=S4Undeformer,
            defomerParameters=lambda deformer: S4DeformerParameters(cast(S4Deformer, deformer)),
            undeformerParameters=lambda undeformer: S4UndeformerParameters(cast(S4Undeformer, undeformer))
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
